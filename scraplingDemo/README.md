# Scrapling × hot：正文抓取补齐 demo

用 [Scrapling](https://github.com/D4Vinci/Scrapling) 的**三级降级**策略，补上 `hot` 项目里
`requests + trafilatura` 抓不下来的那批源。

> 位置：`hot/scraplingDemo/`（独立目录，不参与 `scripts/aggregate.py` 主链路，可安全删除）

| 文件 | 作用 |
|---|---|
| `fetch_hot_sources.py` | 三级降级抓取脚本，可独立运行 |
| `report.html` | 单文件可视化报告，零依赖可离线打开 |
| `result.json` | 最近一次实跑的逐层明细 |

## 背景：hot 现在的正文抓取缺口

`hot/scripts/news_content_extract.py` 用 `requests` + `trafilatura` 抓文章正文。
问题在于这类站点**不会报错**——HTTP 200 返回，管线以为成功了，实际正文是空壳：

| 失败类型 | 表现 | 典型源 |
|---|---|---|
| 安全检测型 | 200，正文是"正在进行安全检测"提示页 | 36氪 |
| SPA 空壳型 | 200，HTML 只有 7KB，正文只剩导航 | 机器之心 |
| WAF 直接拦截 | 403 / SSLError | LINUX DO |

## 实测对比（2026-09-15 实跑）

| 来源 | 老方案 requests+trafilatura | 新方案 Scrapling | 命中层级 | 耗时 |
|---|---|---|---|---|
| 36氪 | 107 字符 ❌ | **5863 字符** ✅ | L2 隐身浏览器 | 10.9s |
| 机器之心 | 0 字符 ❌ | **4302 字符** ✅ | L2 隐身浏览器 | 9.0s |
| LINUX DO | 0 字符（403）❌ | **3508 字符** ✅ | L1 指纹伪装 | 1.1s |
| 量子位（对照组） | 2815 字符 ✅ | 4625 字符 ✅ | L1 指纹伪装 | 0.1s |

**成功率 1/4 → 4/4。**

两个值得注意的点：

1. **LINUX DO 根本不需要浏览器**。老方案 403/SSLError，换成 `Fetcher` 的 Chrome TLS 指纹伪装就
   直接 200，耗时 1.1 秒。这类 WAF 大量存在，是最划算的一档。
2. **只有真 SPA / 真安全检测才需要上浏览器**。36氪 和机器之心必须走 L2 隐身浏览器，
   单篇 9~11 秒。全量 5000+ 篇都走浏览器是不现实的。

## 三级降级策略

```
L1  Fetcher          curl_cffi + Chrome TLS 指纹 + HTTP/3      0.1~1s    覆盖大多数 WAF
L2  StealthyFetcher  隐身浏览器 + 指纹伪装 + 可解 Cloudflare      数秒      应对 JS 安全检测
L3  DynamicFetcher   标准 Playwright/Chrome，跑完整 JS           数秒~数十秒 兜底 SPA
```

每层抓完先判定，够用就停，**不轻易启动浏览器**。

### 判定标准（踩过的坑）

判定条件必须是**正文字符数 ≥ 阈值 且 期望关键词命中**，两个都要。

只卡长度会被假通过骗到：36氪 的拦截页 `markdown()` 原始长度有 **1037 字符**，
看着像是抓到了，实际上其中绝大部分是内嵌 base64 图片的编码；清洗掉 base64 后只剩 **56 字符**。
所以 `clean_markdown()` 先剥 base64 和图片标记，样本再各配一个"正文里必然会出现的词"做验证。

## 怎么跑

```bash
# 准备环境（只需一次）
pip install -e "/path/to/Scrapling[fetchers]"
pip install markdownify requests trafilatura   # markdown() 与对照组需要
scrapling install                              # 下载浏览器内核

# 跑内置样例（4 个源，含老方案对比）
python fetch_hot_sources.py --compare

# 只走 L1，不启动浏览器（快，但反爬站会未过）
python fetch_hot_sources.py --max-level 1

# 跑指定 URL 并落盘
python fetch_hot_sources.py https://36kr.com/xxx --out result.json
```

上次实跑明细见同目录 `result.json`。

## 怎么接进 hot 的管线

`news_content_extract.py` 里那个 `requests.get(url, headers=HEADERS, timeout=20)` 就是替换点：

```python
from fetch_hot_sources import fetch_article   # 把 demo 里的三级降级封装成函数即可

def extract_article(url: str):
    page = fetch_article(url)          # 内部 L1 → L2 → L3 自动降级
    if page is None:
        return None                    # 三级都没拿到，交给上层记录到 meta.json
    return {
        "text": page.markdown(main_content_only=True),   # 顺带得到 RAG 友好格式
        "title": page.css('meta[property="og:title"]::attr(content)').get(),
    }
```

三条落地建议：

1. **不要全量升级**。默认只走 L1，把 L2/L3 交给"L1 未过"的源按需触发；
   浏览器开销是 HTTP 的 50~100 倍，定时任务每 6 小时跑一次扛不住全量浏览器抓取。
2. **优先修来源，而不是修抓取**。像 LINUX DO 这种只是 TLS 指纹被卡的，换 L1 就够了；
   真正需要 L2/L3 的应当控制在少数几个源里。
3. **失败要显性化**。现在的问题不是抓取策略不够强，而是失败无声无息——
   建议给 `news_content_extract.py` 加上"正文字符数 < 阈值就记入 meta.json 的 ❌"，
   这样坏源会自己暴露出来。

## 已知情况

- `solve_cloudflare=True` 在非 Cloudflare 站点上会打 `ERROR: No Cloudflare challenge found.`
  日志，属于正常噪声，不影响结果。
- 36氪 的 L1 结果**不稳定**：有时能裸闯过安全检测（拿到 1035 字符），有时被拦（56 字符）。
  这正是需要降级兜底的原因，不要依赖 L1 的偶然成功。
- 抓取请遵守目标站 robots.txt 与使用条款，控制请求频率。

## 能顺手拿到的额外能力

demo 里没展开、但接管线时值得一并考虑的两件事：

- **`capture_xhr`**：`Fetcher.get(url, capture_xhr="*/api/*")` 会把页面加载时发出的
  XHR/fetch 响应收进 `page.captured_xhr`，可以直接拿站点自己的接口数据，不用逆向。
- **自适应选择器**：`page.css('.item', auto_save=True)` 记住元素特征，
  网站改版后用 `adaptive=True` 能把元素找回来。对写死选择器的站点采集脚本是刚需。
