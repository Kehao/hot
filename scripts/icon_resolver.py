#!/usr/bin/env python3
"""Resolve real project/model icons for AI热榜 data files.

Rules:
- GitHub repo/project: use owner avatar, never github.com/favicon.ico.
- OpenRouter model: use real provider brand/domain favicon, never OpenRouter favicon.
- Official websites: use Google favicon service for the official domain.
The generated icon_url is an image URL used directly by Hugo templates.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SITE_DATA = ROOT / 'site' / 'data'

PROVIDER_ICON_DOMAINS = {
    'openai': 'openai.com',
    'anthropic': 'anthropic.com',
    'google': 'google.com',
    'deepseek': 'deepseek.com',
    'qwen': 'qwenlm.github.io',
    'alibaba': 'alibabacloud.com',
    'moonshotai': 'moonshot.cn',
    'moonshot': 'moonshot.cn',
    'z-ai': 'z.ai',
    'zhipu': 'z.ai',
    'minimax': 'minimax.io',
    'xiaomi': 'xiaomimimo.com',
    'inclusionai': 'inclusionai.com',
    'mistralai': 'mistral.ai',
    'mistral': 'mistral.ai',
    'x-ai': 'x.ai',
    'xai': 'x.ai',
    'meta-llama': 'ai.meta.com',
    'meta': 'ai.meta.com',
    'nvidia': 'nvidia.com',
    'amazon': 'aws.amazon.com',
    'bytedance-seed': 'seed.bytedance.com',
    'bytedance': 'seed.bytedance.com',
    'runway': 'runwayml.com',
    'black-forest-labs': 'blackforestlabs.ai',
    'huggingface': 'huggingface.co',
    'arcee-ai': 'arcee.ai',
    'rekaai': 'reka.ai',
    'liquid': 'liquid.ai',
    'aion-labs': 'aionlabs.ai',
    'allenai': 'allenai.org',
    'relace': 'relace.ai',
    'thedrummer': 'thedrummer.cc',
    'nousresearch': 'nousresearch.com',
    'morph': 'morphllm.com',
    'cohere': 'cohere.com',
    'microsoft': 'microsoft.com',
    'sao10k': 'huggingface.co/Sao10K',
    'inflection': 'inflection.ai',
    'poolside': 'poolside.ai',
    'baidu': 'yiyan.baidu.com',
    'tencent': 'cloud.tencent.com',
    'openrouter': 'openrouter.ai',
    'together': 'together.ai',
    'groq': 'groq.com',
    'siliconflow': 'siliconflow.cn',
    'volcengine': 'volcengine.com',
    'aws-bedrock': 'aws.amazon.com',
    'azure-openai': 'azure.microsoft.com',
}

NAME_ICON_DOMAINS = {
    'cursor': 'cursor.com',
    'github copilot': 'github.com',
    'claude code': 'anthropic.com',
    'claude': 'anthropic.com',
    'codex': 'openai.com',
    'chatgpt': 'openai.com',
    'openai': 'openai.com',
    'gemini': 'gemini.google.com',
    'google': 'google.com',
    'perplexity': 'perplexity.ai',
    'midjourney': 'midjourney.com',
    'runway': 'runwayml.com',
    'kling': 'klingai.com',
    'flux': 'blackforestlabs.ai',
    'qwen': 'qwenlm.github.io',
    'deepseek': 'deepseek.com',
    'kimi': 'moonshot.cn',
    'moonshot': 'moonshot.cn',
    'minimax': 'minimax.io',
    'mimo': 'xiaomimimo.com',
    'xiaomi': 'xiaomimimo.com',
    'ling': 'inclusionai.com',
    'inclusionai': 'inclusionai.com',
    'glm': 'z.ai',
    'z.ai': 'z.ai',
    'grok': 'x.ai',
    'xai': 'x.ai',
    'mistral': 'mistral.ai',
    'llama': 'ai.meta.com',
    'nvidia': 'nvidia.com',
    'hugging face': 'huggingface.co',
    'huggingface': 'huggingface.co',
    'baidu': 'yiyan.baidu.com',
    'tencent': 'cloud.tencent.com',
    'openrouter': 'openrouter.ai',
    'together': 'together.ai',
    'groq': 'groq.com',
    'siliconflow': 'siliconflow.cn',
    'volcengine': 'volcengine.com',
    'aws bedrock': 'aws.amazon.com',
    'azure openai': 'azure.microsoft.com',
}

BAD_ICON_PATTERNS = (
    'openrouter.ai/favicon',
    'github.com/favicon',
    'www.github.com/favicon',
)


def google_favicon(domain: str, size: int = 64) -> str:
    domain = domain.strip().strip('/')
    return f'https://www.google.com/s2/favicons?domain={domain}&sz={size}'


def github_avatar_from_url(url: str) -> str | None:
    try:
        p = urlparse(url)
    except Exception:
        return None
    if p.netloc.lower() not in {'github.com', 'www.github.com'}:
        return None
    parts = [x for x in p.path.split('/') if x]
    if not parts:
        return None
    owner = parts[0]
    if owner.lower() in {'features', 'marketplace', 'topics', 'collections', 'orgs'} and len(parts) > 1:
        # marketing pages are not repos; let name/domain mapping handle them.
        return None
    return f'https://github.com/{owner}.png?size=128'


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ''
    if host.startswith('www.'):
        host = host[4:]
    return host


def provider_prefix_from_openrouter_url(url: str) -> str | None:
    try:
        p = urlparse(url)
    except Exception:
        return None
    if p.netloc.lower() not in {'openrouter.ai', 'www.openrouter.ai'}:
        return None
    parts = [x for x in p.path.split('/') if x]
    return parts[0].lower() if parts else None


def provider_domain_from_text(text: str) -> str | None:
    low = (text or '').lower()
    for key, domain in NAME_ICON_DOMAINS.items():
        if key in low:
            return domain
    return None


def resolve_icon(item: dict, kind: str) -> str:
    url = item.get('url') or ''
    name = item.get('name') or ''
    provider = item.get('provider') or item.get('author') or ''
    source = item.get('source') or ''

    # Providers are curated records. Prefer an explicit brand/logo URL if present;
    # otherwise resolve from the stable provider id/name before looking at a page URL.
    if kind == 'provider':
        for key in ('icon_url', 'logo_url', 'logo'):
            value = str(item.get(key) or '').strip()
            if value.startswith(('http://', 'https://')) and not is_bad_icon(value):
                return value
        pid = str(item.get('id') or '').lower()
        domain = PROVIDER_ICON_DOMAINS.get(pid) or provider_domain_from_text(f'{name} {provider} {source}')
        if domain:
            return google_favicon(domain)

    # OpenRouter model -> provider brand icon, not OpenRouter.
    prefix = provider_prefix_from_openrouter_url(url)
    if prefix:
        domain = PROVIDER_ICON_DOMAINS.get(prefix) or provider_domain_from_text(f'{provider} {name}')
        if domain:
            return google_favicon(domain)

    # HuggingFace model -> org/project avatar-ish image. Use HF avatar endpoint where possible.
    if 'huggingface.co' in domain_from_url(url):
        parts = [x for x in urlparse(url).path.split('/') if x]
        if parts:
            return f'https://huggingface.co/{parts[0]}.png'
        return google_favicon('huggingface.co')

    # GitHub repo/project -> owner avatar, not GitHub favicon.
    gh = github_avatar_from_url(url)
    if gh:
        return gh

    # Known product/provider names override generic domains.
    domain = provider_domain_from_text(f'{name} {provider} {source}')
    if domain:
        return google_favicon(domain)

    host = domain_from_url(url)
    if host and host not in {'github.com', 'openrouter.ai'}:
        return google_favicon(host)

    # Deliberately return an empty string instead of the site favicon. The quality
    # gate treats missing icon_url as actionable, while aihot favicon fallback hides
    # regressions on list pages.
    return ''


def is_bad_icon(icon: str) -> bool:
    low = (icon or '').lower()
    return any(p in low for p in BAD_ICON_PATTERNS) or 'aihot.bt199.com/favicon' in low


def apply_to_file(path: Path, kind: str) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, dict):
        items = data.get('items') or []
    else:
        items = data
    count = 0
    for item in items:
        icon_url = resolve_icon(item, kind)
        if icon_url and item.get('icon_url') != icon_url:
            item['icon_url'] = icon_url
            count += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return count


def sync_site_data(filename: str):
    src = DATA / filename
    dst = SITE_DATA / filename
    if src.exists() and dst.parent.exists():
        dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')


def main():
    changed = 0
    changed += apply_to_file(DATA / 'providers.json', 'provider')
    changed += apply_to_file(DATA / 'models_curated.json', 'model')
    changed += apply_to_file(DATA / 'tools.json', 'tool')
    changed += apply_to_file(DATA / 'agents.json', 'agent')
    for name in ['providers.json', 'models_curated.json', 'tools.json', 'agents.json']:
        sync_site_data(name)
    print(f'resolved icon_url for {changed} entries')


if __name__ == '__main__':
    main()
