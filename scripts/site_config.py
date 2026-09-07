#!/usr/bin/env python3
"""站点对外地址唯一数据源。

仓库根目录 `CNAME` 文件统一存放站点地址,支持三种写法:
- 裸域名:     hot.kehao.info        → https://hot.kehao.info
- 裸 IPv4:    47.114.36.224          → http://47.114.36.224   (IP 默认无 TLS,故用 http)
- 带协议:     https://hot.kehao.info 或 http://47.114.36.224 (按实际部署自行指定)

所有脚本/质量门禁/构建从这里读取 host 与 url,避免域名散落硬编码。
改站点地址时只需改 CNAME 一个文件。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 历史部署中曾使用的站点域名。即便 CNAME 已更换,数据/模板里仍可能残留,
# 质量门禁与图标黑名单需继续识别,防止把旧站点默认 favicon 当成有效图标。
LEGACY_HOSTS = ('aihot.bt199.com',)

_IPV4_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')


def _raw() -> str:
    """读取 CNAME 原始内容并规整:去首尾空白、去尾部斜杠。"""
    try:
        text = (ROOT / 'CNAME').read_text(encoding='utf-8').strip()
    except OSError:
        text = ''
    return text.rstrip('/')


def host() -> str:
    """返回裸主机名/IP,不带协议与斜杠。读取失败时回退历史域名。"""
    raw = _raw()
    if '://' in raw:
        raw = raw.split('://', 1)[1]
    host_part = raw.split('/', 1)[0].strip()
    if not host_part:
        return LEGACY_HOSTS[0]
    return host_part


def scheme() -> str:
    """返回协议。CNAME 已写协议则尊重;否则域名按 https,裸 IPv4 按 http。"""
    raw = _raw()
    if raw.startswith('http://'):
        return 'http'
    if raw.startswith('https://'):
        return 'https'
    return 'http' if _IPV4_RE.match(host()) else 'https'


def url() -> str:
    """返回带协议、无尾斜杠的完整站点地址,如 https://hot.kehao.info。"""
    return f'{scheme()}://{host()}'


def base_url() -> str:
    """返回 Hugo baseURL 格式(末尾带斜杠)。"""
    return url() + '/'


def favicon_fragments() -> tuple[str, ...]:
    """站点自身 favicon 的 URL 片段(当前 host + 历史域名),用于图标黑名单/门禁。"""
    frags = {f'{host()}/favicon'}
    frags.update(f'{h}/favicon' for h in LEGACY_HOSTS)
    return tuple(sorted(frags))


if __name__ == '__main__':
    print(f'host      = {host()}')
    print(f'scheme    = {scheme()}')
    print(f'url       = {url()}')
    print(f'base_url  = {base_url()}')
    print(f'favicons  = {favicon_fragments()}')
