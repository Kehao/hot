#!/usr/bin/env python3
"""
AI热榜 - 主聚合器 v3.1
=====================
【这是什么】
  本项目的"数据链总编排入口"：把 30+ 个采集/处理/增强模块按固定顺序串起来跑，
  每 6 小时由服务器 cron 调用一次（入口脚本见服务器 /usr/local/bin/hot-deploy.sh，
  其核心一步就是运行本文件）。

【数据流全景（先看这个再读代码）】
  上游源(RSS/API/GitHub/HF/关键词/Agent)
        │  Phase 1 数据采集：抓原始数据落盘
        ▼
  data/*.json（news.json 等 18 个产物，详见下方"阶段说明"）
        │  Phase 2 数据处理 + Phase 3 AI 增强：清洗/加工/回写
        ▼
  data/*.json（被逐步增强，news.json 是"滚雪球"文件）
        │  Phase 4 同步部署：算榜单、生成内容页、镜像到 site/data
        ▼
  site/data/*（Hugo 模板直接消费）→ hugo build → 静态页发布

【运行结果去哪看】
  每一步成功/失败都会记录进 data/meta.json 的 results 字段，
  排查问题先看它（python -c "import json;print(json.load(open('data/meta.json'))['results'])"）。

【四个阶段的设计意图】
  串行 + 每步独立 try/except：单步失败不影响后续步骤，
  保证"抓取挂了也能出昨天的榜"，meta.json 会如实标出 ❌。
"""

import os
import sys
import json
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

# 把 scripts/ 目录本身加入模块搜索路径，
# 这样下方 `from news_rss import ...` 才能找到同目录的兄弟模块。
# （本文件运行时通常位于 scripts/ 下；若从其它目录 import 也能定位。）
sys.path.insert(0, os.path.dirname(__file__))

# ------------------------------------------------------------------
# 模块导入区：顺序与原始文件保持一致（勿随意重排，防止遗漏 import）。
# 每个模块的职责标注如下，理解顺序 = 理解全链路：
# ------------------------------------------------------------------
from news_rss import collect_rss_news                    # [P1·采集] RSS 源抓新闻 → news.json
from news_api import collect_api_news                    # [P1·采集] 新闻 API → news.json
from news_interleave import interleave_news              # [P1·采集] 多源去重/穿插排序 → news.json
from github_discover import discover_github_projects     # [P1·采集] GitHub 项目 → projects.json
from github_trending import track_github_trending        # [P1·采集] GitHub 趋势 → trending.json
from huggingface_discover import discover_hf_models      # [P1·采集] HF 模型 → models.json
from refine_models import refine_models                  # [P2·处理] 精简/清洗模型池 → models.json
from generate_curated_models import generate_curated_models  # [P2·处理] 精选模型榜 → models_curated.json
from generate_rising import generate_rising              # [P2·处理] 热度飙升榜 → rising.json
from keyword_collector import collect_keywords           # [P1·采集] SEO 关键词 → keywords.json/seo.json
from agent_discover import discover_agents               # [P1·采集] Agent 发现 → agents.json
from trending_scorer import compute_trending             # [P4·部署] 今日热度榜 → hot.json
from daily_spotlight import select_daily_spotlight       # [P2·处理] 每日精选 → daily.json
from link_checker import quick_check                     # [P2·处理] 外链可用性 → broken_links.json
from ai_enhance import summarize_news, generate_daily_briefing, score_tools  # [P3·AI] 摘要/每日快报/工具评分
from generate_sitemap import generate_sitemap            # [P4·部署] → sitemap.xml
from generate_tool_pages import generate_tool_pages      # [P4·部署] 工具详情页 → content/tools/*.md
from generate_news_pages import generate_news_pages      # [P4·部署] 新闻详情页 → content/news/*.md
from news_content_extract import extract_news_content    # [P3·AI] 正文抽取 → 回写 news.json
from news_article_enhance import enhance_news            # [P3·AI] 站内长文增强 → 回写 news.json
from news_rewrite import process_news                    # [P3·AI] 标题/摘要洗稿 → 回写 news.json
from openrouter_providers import update_providers        # [P2·处理] 提供商快照 → providers.json
from enrich_hot_data import enrich_hot_data              # [P4·部署] 热点站内化 → 回写 news/hot
from update_readme_links import update_readme_links      # [P4·部署] 重刷 README 时间/热点

# ------------------------------------------------------------------
# 路径常量
# ------------------------------------------------------------------
# 数据仓库目录：scripts/aggregate.py → ../data，即项目根下的 data/
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
# Hugo 站点数据目录：../site/data，是 data/ 的"镜像"（模板从这里读数）
SITE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "data")
# 全站统一使用上海时区，避免服务器时区差异导致时间戳漂移
SH_TZ = ZoneInfo("Asia/Shanghai")


def sh_now():
    """返回上海时区的当前时间（datetime 对象）。"""
    return datetime.now(SH_TZ)


def sync_to_site():
    """
    把 data/ 下所有 .json 拷贝到 site/data/（Hugo 的 data 目录）。

    为什么需要这一步：
      - scripts/ 流水线只认 data/（自己人目录）；
      - Hugo 构建时只会把 site/data/ 里的 json 自动加载为 site.Data.xxx 供模板使用。
    因此 data/ 与 site/data/ 是"源与镜像"的关系，改其一不会自动同步到另一个，
    必须由本函数搬运——这也是"数据契约"的一环。
    """
    if not os.path.exists(SITE_DATA_DIR):
        os.makedirs(SITE_DATA_DIR)

    count = 0
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            src = os.path.join(DATA_DIR, filename)
            dst = os.path.join(SITE_DATA_DIR, filename)
            shutil.copy2(src, dst)
            count += 1

    return f"同步 {count} 个文件到 site/data/"


def write_meta(now, results):
    """
    写入运行总账 data/meta.json（并同步一份到 site/data/meta.json）。

    meta.json 是全项目最重要的"体检报告"：
      - last_update：本轮完成时间（首页/README 的"最近更新"读的就是它）
      - results：{步骤名: "✅ ..." / "❌ 异常信息"}，一眼看出哪步挂了
    之所以也拷贝到 site/data/，是为了让首页的更新时间在构建后立即可见。
    """
    meta = {
        "last_update": now,
        "version": "3.0",
        "results": results,
    }
    meta_path = os.path.join(DATA_DIR, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if not os.path.exists(SITE_DATA_DIR):
        os.makedirs(SITE_DATA_DIR)
    shutil.copy2(meta_path, os.path.join(SITE_DATA_DIR, "meta.json"))


def main():
    """主流程：按 Phase 1→2→3→4 顺序串行执行全部步骤，并汇总成败写入 meta.json。"""
    now = sh_now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🚀 AI热榜数据采集 v3.0 - {now}")
    print("=" * 50)

    # --------------------------------------------------------------
    # Phase 1: 数据采集 —— 从各上游源抓原始数据，首次落盘
    # 列表元素 = (控制台显示名, 函数)；函数约定：无参、可独立运行、返回描述字符串
    # --------------------------------------------------------------
    print("\n📡 Phase 1: 数据采集")
    steps_collect = [
        ("📰 RSS新闻", collect_rss_news),          # 抓 RSS 源 → 写 news.json
        ("📰 API新闻", collect_api_news),          # 抓新闻 API → 写 news.json
        ("🔀 新闻穿插", interleave_news),          # 多源去重/排序 → 回写 news.json
        ("🔍 GitHub项目", discover_github_projects),   # → projects.json
        ("📈 GitHub热度", track_github_trending),      # → trending.json
        ("🤗 HF模型", discover_hf_models),             # → models.json
        ("🔑 关键词", collect_keywords),               # → keywords.json / seo.json
        ("🤖 Agent发现", discover_agents),             # → agents.json
    ]

    # --------------------------------------------------------------
    # Phase 2: 数据处理 —— 纯本地加工，不调外部 LLM，速度快
    # --------------------------------------------------------------
    print("\n⚙️ Phase 2: 数据处理")
    steps_process = [
        ("🧹 模型精简", refine_models),                # 清洗 models.json
        ("🏆 模型精选榜", generate_curated_models),    # → models_curated.json
        ("📈 热度飙升", generate_rising),              # → rising.json
        ("🏢 提供商更新", update_providers),          # → providers.json
        ("⭐ 每日精选", select_daily_spotlight),      # → daily.json
        ("🔗 链接检查", quick_check),                 # → broken_links.json
    ]

    # --------------------------------------------------------------
    # Phase 3: AI 增强 —— 调 LLM(OpenRouter)，最慢最耗资源的一阶段；
    # 对同一份 news.json 反复"滚雪球"式回写：摘要→正文→增强→洗稿，字段逐步补全。
    # --------------------------------------------------------------
    print("\n🤖 Phase 3: AI 增强")
    steps_ai = [
        ("📝 新闻摘要", summarize_news),              # 回写 news.json：ai_summary
        ("📄 正文抽取", extract_news_content),        # 回写 news.json：content_text
        ("✍️ 新闻文章增强", enhance_news),            # 回写 news.json：站内长文内容
        ("🔄 新闻洗稿", process_news),                # 回写 news.json：rewritten 标题/摘要
        ("📰 每日快报", generate_daily_briefing),     # → briefing.json
        ("⭐ 工具评分", score_tools),                 # 回写 tools.json：评分
    ]

    # --------------------------------------------------------------
    # Phase 4: 同步部署 —— 把加工好的数据"变现"成站点产物：
    # 算热度榜、生成上千个内容页 md、镜像数据、刷新 sitemap/README。
    # --------------------------------------------------------------
    print("\n🚀 Phase 4: 同步部署")
    steps_deploy = [
        ("🔥 今日热点", compute_trending),            # → hot.json（首页今日热点）
        ("🔗 热点新闻站内化", enrich_hot_data),       # 回写 news/hot：补内部详情页链接
        ("🧱 生成工具静态页", generate_tool_pages),   # → site/content/tools/*.md
        ("📰 生成新闻静态页", generate_news_pages),   # → site/content/news/*.md(数千篇)
        ("📦 同步数据", sync_to_site),                # data/*.json → site/data/
        ("🗺️ 生成Sitemap", generate_sitemap),         # → site/static/sitemap.xml
        ("📘 更新README", update_readme_links),       # 重刷 README 时间/热点
    ]

    # 四个阶段合流，组成最终执行序列
    all_steps = [
        ("📡 数据采集", steps_collect),
        ("⚙️ 数据处理", steps_process),
        ("🤖 AI 增强", steps_ai),
        ("🚀 同步部署", steps_deploy),
    ]

    # --------------------------------------------------------------
    # 统一执行器：逐阶段、逐步串行运行。
    # 容错设计：每个 func 都包 try/except，单步异常只记为 ❌ 并继续下一步——
    # 保证"AI 增强挂了，今天的榜照样能出"，只是少了几项增强字段。
    # --------------------------------------------------------------
    results = {}
    for phase_name, phase_steps in all_steps:
        for name, func in phase_steps:
            try:
                print(f"  {name}...")
                result = func()
                results[name] = f"✅ {result}"
                print(f"    → {result}")
            except Exception as e:
                results[name] = f"❌ {e}"
                print(f"    → ❌ {e}")

    # 汇总本轮成败数（meta.json 里也会体现）
    print("\n" + "=" * 50)
    success = sum(1 for v in results.values() if v.startswith("✅"))
    fail = sum(1 for v in results.values() if v.startswith("❌"))
    print(f"📊 结果: {success} 成功 / {fail} 失败 / {len(results)} 总计")

    # 写入元数据（同时同步到 site/data，确保首页更新时间立即可见）
    finish_time = sh_now().strftime('%Y-%m-%d %H:%M:%S')
    write_meta(finish_time, results)

    # README 依赖 meta.last_update。必须在最终 meta 写入后再刷新一次，
    # 否则质量门禁会看到 README 仍停留在上一轮日期，导致定时任务失败并发邮件。
    # 换言之：README 里的"最近更新"要读本轮新 meta，所以 README 刷新必须放在
    # 第一次 write_meta 之后（否则用的是旧时间，quality_gate 会判定不一致）。
    try:
        result = update_readme_links()
        results["📘 更新README"] = f"✅ {result}"
        print(f"  📘 最终同步README...\n    → {result}")
    except Exception as e:
        results["📘 更新README"] = f"❌ {e}"
        print(f"  📘 最终同步README...\n    → ❌ {e}")

    # 记录最终 README 同步结果，避免 meta.results 留下过期状态。
    # （第一次 write_meta 时 README 还没刷，results 里的 README 是 Phase 4 旧值；
    #   这里用最新 results 再写一次，保证 meta 与实际一致。）
    write_meta(finish_time, results)

    print(f"\n✅ 采集流程结束 - {finish_time}")


if __name__ == "__main__":
    # 直接运行本文件（.venv/bin/python scripts/aggregate.py）即触发全流程；
    # 被其它脚本 import 时不自动执行。
    main()
