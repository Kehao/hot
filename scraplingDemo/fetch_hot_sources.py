#!/usr/bin/env python3
"""
Scrapling × hot 项目：AI 新闻正文抓取补齐 demo
=============================================

【要解决的问题】
hot/scripts/news_content_extract.py 目前用 requests + trafilatura 抓正文，
遇到下面几类站点会「静默失败」——HTTP 200，但正文是空壳或拦截页，管线察觉不到：

  1. 安全检测型（36氪）     → 200，正文其实是"正在进行安全检测"提示页
  2. SPA 空壳型（机器之心）  → 200，HTML 只有 7KB，正文只剩导航
  3. WAF 直接拦截型（LINUX DO）→ 403 / SSLError

【本 demo 的做法：按需三级降级】
  L1  Fetcher          curl_cffi + Chrome TLS 指纹 + HTTP/3     约 0.1~1 秒
  L2  StealthyFetcher  隐身浏览器 + 指纹伪装 + 可过 Cloudflare    约数秒
  L3  DynamicFetcher   标准 Playwright / Chrome，跑完整 JS       约数秒~数十秒
  规则：每层抓完先判定是否拿到正文，够用就停 —— 保证大多数站点仍走 L1，不启动浏览器。

【判定标准（重要）】
  「抓到正文」= 清洗后正文字符数 >= MIN_BODY_CHARS
                且（若该样本配了 expect 关键词）关键词必须命中。
  只卡长度会被假通过骗到：36氪 的拦截页 markdown 原始长度有 1037 字符，
  但其中绝大部分是 base64 内嵌图片，清洗后只剩 56 字符。

用法：
  python fetch_hot_sources.py                     # 跑内置的 4 个源样例
  python fetch_hot_sources.py <url> [<url> ...]   # 跑指定 URL
  python fetch_hot_sources.py --compare           # 同时跑老方案 requests+trafilatura 做对比
  python fetch_hot_sources.py --max-level 1       # 只用 L1（不启动浏览器，最快）
  python fetch_hot_sources.py --out result.json   # 结果落盘
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Callable

# ----------------------------------------------------------------------------
# 配置
# ----------------------------------------------------------------------------
MIN_BODY_CHARS = 600  # 正文判定阈值：清洗后正文字符数低于它就算「没抓到」

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# 内嵌 base64 图片会把 markdown 撑出几千字符，统计前必须先清掉
BASE64_IMG_RE = re.compile(r"!\[[^\]]*\]\(data:[^)]{40,}\)")
IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


@dataclass
class Sample:
    """一个抓取目标。expect 是「正文里必然会出现的词」，用来验证真的抓到了内容。"""

    source: str
    url: str
    expect: str = ""


# 内置样例：覆盖 hot 项目里最容易失败的三类源 + 一个正常源作对照
SAMPLES: list[Sample] = [
    Sample("36氪", "https://36kr.com/newsflashes/3925968796514432", "DeepSeek"),
    Sample("机器之心", "https://www.jiqizhixin.com/articles/2026-09-07-3", "AlphaBot"),
    Sample("LINUX DO", "https://linux.do/t/topic/2503616", "中转站"),
    Sample("量子位（对照组，本来就能抓）", "https://www.qbitai.com/2026/09/485525.html", "机器人"),
]


@dataclass
class Attempt:
    """某一层的抓取尝试记录"""

    level: str
    desc: str
    status: int | None = None
    chars: int = 0
    elapsed: float = 0.0
    hit: bool = False
    error: str = ""


@dataclass
class Result:
    """单个 URL 的最终结果"""

    source: str
    url: str
    expect: str = ""
    ok: bool = False
    level: str = ""
    body_chars: int = 0
    elapsed: float = 0.0
    title: str = ""
    markdown_head: str = ""
    baseline_chars: int = -2  # -2 = 未跑对比, -1 = 环境缺依赖
    attempts: list[Attempt] = field(default_factory=list)


# ----------------------------------------------------------------------------
# 三级抓取策略
# ----------------------------------------------------------------------------
def level1(url: str):
    """L1：curl_cffi + 浏览器 TLS 指纹，最轻最快"""
    from scrapling.fetchers import Fetcher

    return Fetcher.get(url, impersonate="chrome", stealthy_headers=True, timeout=30)


def level2(url: str):
    """L2：隐身浏览器（指纹伪装，可解 Cloudflare 人机校验）"""
    from scrapling.fetchers import StealthyFetcher

    return StealthyFetcher.fetch(
        url, headless=True, network_idle=True, solve_cloudflare=True, timeout=60_000
    )


def level3(url: str):
    """L3：标准无头浏览器，完整执行 JS（最重，兜底）"""
    from scrapling.fetchers import DynamicFetcher

    return DynamicFetcher.fetch(url, headless=True, network_idle=True, timeout=60_000)


LEVELS: list[tuple[str, str, Callable[[str], object]]] = [
    ("L1", "Fetcher · TLS 指纹伪装", level1),
    ("L2", "StealthyFetcher · 隐身浏览器", level2),
    ("L3", "DynamicFetcher · 标准浏览器", level3),
]


# ----------------------------------------------------------------------------
# 正文与标题提取
# ----------------------------------------------------------------------------
def clean_markdown(markdown: str) -> str:
    """去掉 base64 内嵌图片和普通图片标记，再压成单行"""
    text = BASE64_IMG_RE.sub(" ", markdown)
    text = IMG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def body_of(page) -> str:
    """优先用 markdown()（LLM 友好，顺便剥掉 prompt 注入内容），失败才退回纯文本。"""
    try:
        return clean_markdown(page.markdown(main_content_only=True))
    except Exception:  # markdownify 未安装时会抛错
        return re.sub(r"\s+", " ", str(page.get_all_text(strip=True))).strip()


def title_of(page) -> str:
    for selector in ('meta[property="og:title"]::attr(content)', "title::text", "h1::text"):
        try:
            value = page.css(selector).get()
        except Exception:
            value = None
        if value and str(value).strip():
            return str(value).strip()
    return ""


def baseline(url: str) -> int:
    """老方案：requests + trafilatura，返回正文字符数（-1 表示环境缺依赖）。"""
    try:
        import requests
        import trafilatura
    except ImportError:
        return -1

    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        text = trafilatura.extract(resp.text, include_comments=False, favor_precision=True) or ""
        return len(re.sub(r"\s+", " ", text).strip())
    except Exception:
        return 0


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def fetch_one(sample: Sample, max_level: int, compare: bool) -> Result:
    result = Result(source=sample.source, url=sample.url, expect=sample.expect)

    if compare:
        result.baseline_chars = baseline(sample.url)

    for idx, (tag, desc, fn) in enumerate(LEVELS, start=1):
        if idx > max_level:
            break

        attempt = Attempt(level=tag, desc=desc)
        start = time.time()
        try:
            page = fn(sample.url)
        except Exception as exc:  # noqa: BLE001
            attempt.elapsed = round(time.time() - start, 1)
            attempt.error = f"{type(exc).__name__}: {str(exc)[:120]}"
            result.attempts.append(attempt)
            continue

        text = body_of(page)
        attempt.status = getattr(page, "status", None)
        attempt.chars = len(text)
        attempt.elapsed = round(time.time() - start, 1)
        attempt.hit = (not sample.expect) or (sample.expect in text)
        result.attempts.append(attempt)

        # 双重判定：长度够 + 关键词命中，才算真的拿到正文
        if attempt.chars >= MIN_BODY_CHARS and attempt.hit:
            result.ok = True
            result.level = tag
            result.body_chars = attempt.chars
            result.elapsed = round(sum(a.elapsed for a in result.attempts), 1)
            result.title = title_of(page)
            result.markdown_head = text[:160]
            return result

    result.elapsed = round(sum(a.elapsed for a in result.attempts), 1)
    return result


def print_block(result: Result, compare: bool) -> None:
    print(f"\n[{result.source}] {result.url}")
    if result.expect:
        print(f"  期望关键词: {result.expect}")

    if compare:
        base = result.baseline_chars
        if base == -1:
            print("  老方案 requests+trafilatura  : 环境缺依赖（pip install requests trafilatura）")
        else:
            mark = "通过" if base >= MIN_BODY_CHARS else "未过"
            print(f"  老方案 requests+trafilatura  : {base:>6} 字符  [{mark}]")

    for attempt in result.attempts:
        if attempt.error:
            print(f"  {attempt.level} {attempt.desc:<26}: 报错 {attempt.error}")
            continue
        mark = "通过" if (attempt.chars >= MIN_BODY_CHARS and attempt.hit) else "未过"
        detail = "" if attempt.hit or not result.expect else "（关键词未命中）"
        print(
            f"  {attempt.level} {attempt.desc:<26}: {attempt.chars:>6} 字符  [{mark}] {detail}"
            f" {attempt.elapsed}s"
        )

    if result.ok:
        print(f"  → 命中 {result.level} | 标题: {result.title[:60]}")
        print(f"  → 正文开头: {result.markdown_head[:100]}...")
    else:
        print("  → 三级全部未拿到正文")


def print_summary(results: list[Result], compare: bool) -> None:
    print("\n" + "=" * 82)
    print("汇总")
    print("=" * 82)
    header = f"{'来源':<26}{'老方案':>10}{'新方案':>10}{'层级':>6}{'耗时':>9}"
    print(header)
    print("-" * 82)
    for result in results:
        old = "-" if result.baseline_chars < 0 else (str(result.baseline_chars) if compare else "-")
        new = str(result.body_chars) if result.ok else "失败"
        print(
            f"{result.source[:24]:<26}{old:>10}{new:>10}{result.level or '-':>6}"
            f"{(str(result.elapsed) + 's'):>9}"
        )
    print("-" * 82)
    new_ok = sum(1 for r in results if r.ok)
    if compare:
        old_ok = sum(1 for r in results if r.baseline_chars >= MIN_BODY_CHARS)
        print(f"成功率：老方案 {old_ok}/{len(results)}   →   新方案 {new_ok}/{len(results)}")
    else:
        print(f"成功率：{new_ok}/{len(results)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrapling × hot 正文抓取补齐 demo")
    parser.add_argument("urls", nargs="*", help="要抓的 URL；不传则跑内置样例")
    parser.add_argument("--compare", action="store_true", help="同时跑老方案 requests+trafilatura")
    parser.add_argument(
        "--max-level",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="最高用到第几级（1 = 只用 HTTP 指纹伪装，不启动浏览器）",
    )
    parser.add_argument("--out", help="结果写入 JSON 文件的路径")
    args = parser.parse_args()

    samples = [Sample(u, u) for u in args.urls] if args.urls else SAMPLES

    print(f"共 {len(samples)} 个目标 | 正文阈值 {MIN_BODY_CHARS} 字符 | 最高层级 L{args.max_level}")

    results = [fetch_one(s, args.max_level, args.compare) for s in samples]
    for result in results:
        print_block(result, args.compare)
    print_summary(results, args.compare)

    if args.out:
        payload = [
            {**asdict(r), "attempts": [asdict(a) for a in r.attempts]} for r in results
        ]
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"\n明细已写入 {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
