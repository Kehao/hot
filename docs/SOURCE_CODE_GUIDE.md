# 读懂 AI热榜 源码指南

> 面向第一次接触本仓库的开发者。目标：30 分钟内建立心智模型，1 小时能定位任意"数据从哪来、到哪去"。
> 配套：`docs/ALIYUN_DEPLOYMENT.md`（部署）、`docs/PIPELINE_RATE_LIMIT.md`（流水线加固）。

---

## 0. 心智模型：这是"两条链"拼起来的站

```
┌─ 数据链(Python, scripts/) ─────────────────────────────┐
│  每 6h: 抓取源 → 聚合/增强 → 产出 data/*.json(18个)     │
│                          ↘ 再生成 content/*.md(4000+)  │
└─────────────────────────────────────────────────────────┘
                    ↓ 拷贝到 site/data/ (sync_to_site)
┌─ 渲染链(Hugo, site/) ──────────────────────────────────┐
│  site/data JSON + site/content md → layouts 模板        │
│  → hugo build → public/ 静态页 → rsync → Nginx          │
└─────────────────────────────────────────────────────────┘
```

一句话：**Python 负责"造数据"，Hugo 负责"把数据变成网页"，两者通过 JSON 文件解耦。**

---

## 1. 目录地图

| 目录/文件 | 职责 | 备注 |
|---|---|---|
| `scripts/` | Python 数据流水线（35 个模块） | 核心代码，按 aggregate 四阶段组织 |
| `scripts/aggregate.py` | **总编排入口** | 串行调用 30+ 模块，4 阶段 |
| `data/` | 流水线产物（18 个 JSON） | news.json 最大约 29MB |
| `site/` | Hugo 站点工程 | |
| `site/data/` | data/ 的镜像（供模板取数） | `sync_to_site()` 自动拷贝 |
| `site/layouts/` | HTML 模板 | index/baseof/list/single |
| `site/content/` | 内容页（news 4022 篇 / tools 172 个） | **news、tools 由流水线自动生成，别手改** |
| `site/static/` | 静态资源（logo、favicon、js/css） | |
| `site/public/` | hugo 构建输出 | rsync 发布源 |
| `tests/` | pytest 回归测试（8 个文件） | 质量门禁配套 |
| `docs/` | 设计/部署/复盘文档 | 读源码前建议先扫 |
| `CNAME` | 域名 hot.kehao.info | 已被 site_config.py 等读取 |

---

## 2. 两条链的详细旅程

### 数据链：aggregate.py 的四阶段（见源码 main()）

每个阶段是一组 `(名字, 函数)`，逐个 try/except 执行，结果写入 `data/meta.json` 的 `results`。
**看 meta.json 就能知道上一轮哪步成功、哪步失败**——这是最快的健康检查入口。

| 阶段 | 代表模块 | 干什么 | 主要产物 |
|---|---|---|---|
| ① 数据采集 | news_rss / news_api / github_discover / huggingface_discover / agent_discover / keyword_collector | 从 RSS、API、GitHub、HF 等抓原始数据 | news.json / projects.json / models.json / agents.json / keywords.json |
| ② 数据处理 | news_interleave / refine_models / generate_curated_models / generate_rising / daily_spotlight / link_checker / openrouter_providers | 去重排序、精简模型、算飙升榜、每日精选、死链检查 | models_curated.json / rising.json / daily.json / broken_links.json / providers.json |
| ③ AI 增强 | ai_enhance / news_content_extract / news_article_enhance / news_rewrite | 用 LLM 做摘要、正文抽取、改写（OpenRouter 通道） | 回写 news.json 各字段（summary/content_text/rewritten） |
| ④ 同步部署 | trending_scorer / enrich_hot_data / generate_tool_pages / generate_news_pages / generate_sitemap / sync_to_site / update_readme_links | 算今日热度榜、生成**内容页 md**、同步 site/data、更新 README | hot.json / content/*.md / site/data/* |

> 关键认知：**news.json 是"滚雪球"文件**——采集(①)创建，之后 news_interleave→正文抽取→增强→洗稿→摘要 每步都回写同一文件、逐步补字段。

### 渲染链：Hugo 怎么消费数据

- `site/layouts/index.html`：首页，直接 `site.Data.xxx` 读 JSON（Hugo 把 site/data 的 json 自动加载为 Data 对象）
- `site/layouts/_default/baseof.html`：全站骨架（方向 C 设计，白底 + 品牌橙 #FF6B35）
- `content/news/xxx.md`：单篇新闻页（由 generate_news_pages 生成，front matter 带 seo 字段）
- 列表/详情模板：list.html、single.html、search.html

**模板里怎么取数**：`{{ $news := slice }}{{ with site.Data.news }}{{ $news = . }}{{ end }}` →
`{{ range first 10 $news }}...{{ end }}`。

---

## 3. 数据契约速查（谁产出哪个 JSON）

主生产者（同一 json 常有多个模块读写，此处列"源头"）：

| 数据文件 | 源头模块 | 说明 |
|---|---|---|
| news.json | news_rss + news_api | 3860+ 条新闻，逐级增强 |
| hot.json | trending_scorer → enrich_hot_data | 首页今日热点（items/top_20） |
| trending.json | github_trending | GitHub 趋势 |
| projects.json | github_discover + github_trending | 开源项目 |
| models.json | huggingface_discover → refine_models | HF 模型池 |
| models_curated.json | generate_curated_models | 精选模型榜 |
| agents.json | agent_discover | Agent 目录 |
| tools.json | 人工(add_tools) + ai_enhance(score_tools) | 工具库（可带评分） |
| providers.json | openrouter_providers | 模型提供商 |
| keywords.json / seo.json | keyword_collector | SEO 关键词 |
| daily.json | daily_spotlight | 每日精选 |
| briefing.json | ai_enhance(generate_daily_briefing) | 每日快报 |
| rising.json | generate_rising | 热度飙升榜 |
| broken_links.json | link_checker | 死链报告 |
| meta.json | aggregate | 运行结果总账（先看它！） |
| content/news/*.md | generate_news_pages | 新闻详情页（自动生成） |
| content/tools/*.md | generate_tool_pages | 工具详情页（自动生成） |

> 注意区分：`data/` 里另有 `resp.json`、`news_cover_raw_results.json`、`chatgpt_cookies.json` 等**调试残留/封面图流水线专属**文件，不参与站点渲染，可忽略。

---

## 4. 推荐阅读路线（5 站，按此顺序）

1. **入口**：读 `scripts/aggregate.py` 的 `main()`（180 行内）——先看 4 个阶段列表，不深入任何模块。
2. **一个采集模块**：`scripts/news_rss.py`——理解"一条新闻怎么进 news.json"（requests 抓 RSS → 解析 → 字段规范化 → 写入）。
3. **一个加工模块**：`scripts/trending_scorer.py` + 打开 `data/hot.json` 对照——理解"热度分数从哪来"（score 字段）。
4. **一个渲染页**：`site/layouts/index.html` + `site/layouts/_default/baseof.html`——理解"JSON 怎么变成 HTML"。
5. **门禁与测试**：`scripts/quality_gate.py`（不达标即失败）、`scripts/sanitize_secrets.py`（提交前清密钥）、`tests/` 挑 1-2 个看断言风格。

看完这 5 站，再看任何模块都能"对号入座"。

---

## 5. 边读边验证的 5 个工具

| 想确认的事 | 怎么做 |
|---|---|
| 上一轮流水线各阶段成败 | `python -c "import json;print(json.load(open('data/meta.json'))['results'])"` |
| 单个模块能否独立跑 | 多数模块有 `__main__`：`.venv/bin/python scripts/xxx.py` |
| 数据长什么样 | `python -c "import json;d=json.load(open('data/hot.json'));print(json.dumps(d,ensure_ascii=False,indent=1)[:1500])"` |
| 页面渲染效果 | `hugo server -s site`（本地预览） |
| 有没有改坏东西 | `.venv/bin/python -m pytest tests/ -q` |

> 完整跑一遍全链路：`.venv/bin/python scripts/aggregate.py`（耗时 20-30 分钟，服务器上的 cron 入口是 `/usr/local/bin/hot-deploy.sh`，含 fetch→aggregate→sanitize→quality→hugo→rsync）。

---

## 6. 易混淆点速记

- `data/` 与 `site/data/` 是**镜像关系**，流水线靠 `sync_to_site()` 同步，手动改其一不会自动同步到另一个。
- `content/news/` 4000+ md 是**生成产物**，改它会被下一轮覆盖；要改版式改 layouts，要改内容改生成逻辑。
- GitHub 上的 data 由 **Actions 自动提交**，服务器每次只 `fetch + reset --hard`，**不要在服务器上 git add**（详见部署文档）。
- AI 增强走 **OpenRouter**，密钥在 env/本地配置；`sanitize_secrets.py` 保证提交到 GitHub 前清除。
- 服务器 cron 实际命令见 `docs/PIPELINE_RATE_LIMIT.md` 第九节（flock 防重入 + 25 分错峰）。
