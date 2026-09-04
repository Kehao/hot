#!/usr/bin/env python3
import json
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import site_config as _sc                      # python scripts/xxx.py / aggregate 同目录导入
except ImportError:
    import scripts.site_config as _sc              # tests 从仓库根以 scripts.xxx 包方式导入

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / 'README.md'
HOT = ROOT / 'data' / 'hot.json'
BRIEFING = ROOT / 'data' / 'briefing.json'
RISING = ROOT / 'data' / 'rising.json'
META = ROOT / 'data' / 'meta.json'

# 站点地址随 CNAME 变化;正则用通用协议匹配,兼容旧 README 中残留的历史域名
BASE = _sc.url()
_ANY_URL = r'https?://[^)\s]+'

# 本站地址的判定:当前 CNAME host + 历史域名。README 顶部静态导航区(badge / 在线网站 /
# 站内搜索 / 立即进入等手工维护区)里的本站链接统一改写为 CNAME 当前地址;第三方推广链接
# (小米/火山/硅基流动等)与 shields.io 徽章图地址不受影响。
_SITE_HOSTS = '|'.join(re.escape(h) for h in {_sc.host(), *_sc.LEGACY_HOSTS})
_SITE_URL_RE = re.compile(rf'https?://(?:{_SITE_HOSTS})(/[^\s)]*?)?(?=[)\s。，：;、）]|$)')


def _rewrite_site_urls(text: str) -> str:
    """把文本中所有指向本站的 URL(含 markdown 链接目标与裸地址)改写为 CNAME 当前地址。"""

    def _repl(mm: re.Match) -> str:
        return BASE + (mm.group(1) or '')

    return _SITE_URL_RE.sub(_repl, text)


def _clean_hot_summary(item):
    text = (item.get('ai_summary') or item.get('subtitle') or item.get('description') or '').strip()
    text = re.sub(r'\s+', ' ', text)
    return text[:80]


def _format_hot_meta(item):
    source = item.get('source', '')
    time = item.get('time') or item.get('detail') or ''
    tags = item.get('tags') or []
    tags_text = ' / '.join(tags[:3])
    parts = [x for x in [source, time, tags_text] if x]
    return ' · '.join(parts)


def update_readme_links():
    if not README.exists() or not HOT.exists():
        return '缺少 README.md 或 hot.json'

    text = README.read_text(encoding='utf-8')
    # 顶部静态导航区(手工维护)随 CNAME 一并同步,保证 README 内站点地址处处一致
    text = _rewrite_site_urls(text)
    hot = json.loads(HOT.read_text(encoding='utf-8'))
    briefing = json.loads(BRIEFING.read_text(encoding='utf-8')) if BRIEFING.exists() else {}
    rising = json.loads(RISING.read_text(encoding='utf-8')) if RISING.exists() else {}
    items = hot.get('items') or hot.get('top_20') or hot.get('hot_list') or []

    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    last_update = meta.get('last_update') or datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    text = re.sub(r'🕐 \*\*最近更新\*\*：.*', f'🕐 **最近更新**：{last_update}', text)

    hot_lines = ['## 🔥 今日热点', '']
    for rank, item in enumerate(items[:10], start=1):
        target = item.get('internal_url') if item.get('type') == 'news' and item.get('internal_url') else item.get('url')
        title = item.get('title_zh') or item.get('title') or item.get('name') or '未命名'
        summary_line = _clean_hot_summary(item)
        meta_line = _format_hot_meta(item)
        hot_lines.append(f'{rank}. [{title}]({target})')
        if summary_line:
            hot_lines.append(f'   - {summary_line}')
        if meta_line:
            hot_lines.append(f'   - `{meta_line}`')
        hot_lines.append('')

    hot_block = '\n'.join(hot_lines).rstrip()
    text = re.sub(r'## 🔥 今日热点[\s\S]*?(?=\n## )', hot_block + '\n\n', text, count=1)

    summary = briefing.get('content', '').strip()
    emoji = briefing.get('emoji', '⚡')
    date = briefing.get('date', '')
    news_count = briefing.get('news_count', '')
    briefing_block = f'''## 🤖 AI 简报\n\n> {emoji} {summary}\n\n`基于 {news_count} 条新闻 · {date}`\n\n👉 [去网站看完整 AI 新闻与站内文章 →]({BASE}/news/)'''

    text = re.sub(rf'## 🤖 每日 AI 快报[\s\S]*?👉 \[去网站看完整 AI 日报与更多快报 →\]\({_ANY_URL}/news/\)', briefing_block, text)

    rising_items = rising.get('items') or []
    rising_lines = []
    for item in rising_items[:5]:
        rising_lines.append(f"- [{item.get('name','未命名')}]({item.get('url', BASE + '/')})：{item.get('reason','最近值得关注')}")
    rising_window = rising.get('window_days', 7)
    rising_block = f"## 📈 热度飙升\n\n" + "\n".join(rising_lines) + f"\n\n👉 [去网站看完整热度飙升榜单 →]({BASE}/)"
    text = re.sub(rf'## 📈 热度飙升[\s\S]*?👉 \[去网站看完整热度飙升榜单 →\]\({_ANY_URL}/\)', rising_block, text)

    # 统一以单个换行结尾(rstrip 保证重复运行不会累加空行)
    README.write_text(text.rstrip('\n') + '\n', encoding='utf-8')
    return 'README 顶部导航、热点链接、AI 简报与热度飙升已刷新'


if __name__ == '__main__':
    print(update_readme_links())
