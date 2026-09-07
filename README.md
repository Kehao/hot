# 🔥 AI热榜

> 每 6 小时自动更新的「中文 AI 世界」热榜与导航站 —— **AI 新闻聚合 + AI 工具 / 大模型 / Agent 导航**。
>
> 线上站点：<https://hot.kehao.info>

🕐 **最近更新**：2026-09-08 04:57:31

> 站点数据由管道每 6 小时自动刷新，此行显示最新一次成功更新（数据管道自动维护，勿手改）。

---

本项目是 **Python 数据管道（`scripts/`）+ Hugo 静态站（`site/`）** 的组合：

- **数据管道**每 6 小时抓取 RSS / 新闻 API / GitHub / HuggingFace / SEO 关键词 / Agent 等 30+ 上游源，经清洗、去重、AI 增强后产出 `data/*.json`；
- **Hugo 站点**消费数据渲染成数千页的纯静态站（新闻站内文、工具 / 模型 / Agent 详情页、各类榜单、站内搜索、sitemap），自动发布到 GitHub Pages（或自托管到阿里云 ECS + Nginx）。

## 目录

- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [数据管道四阶段流水线](#数据管道四阶段流水线)
- [Hugo 站点与构建](#hugo-站点与构建)
- [质量保障](#质量保障)
- [本地快速开始](#本地快速开始)
- [部署](#部署)
  - [GitHub Actions 自动部署](#github-actions-自动部署)
  - [阿里云自托管方案](#阿里云自托管方案)
  - [切换域名](#切换域名)
- [crontab 生产实例](#crontab-生产实例)
- [实战踩坑记录](#实战踩坑记录)
- [相关文档](#相关文档)

---

## 核心特性

| 特性 | 说明 |
|---|---|
| 🕐 每 6 小时自动更新 | 新闻滚动收录、榜单重算、站点重建发布，全程无人值守 |
| 📰 AI 新闻聚合 | 多源 RSS + 新闻 API 抓取，正文抽取后由 LLM 翻译改写为中文站内长文 |
| 🔥 今日热点榜 | 依据多源热度的加权评分产出 Top10，标题 / 摘要均中文 |
| 🧰 AI 工具 / 模型 / Agent 导航 | 收录数百工具与模型，分类页 + 精选榜 + 详情页 |
| 🔑 SEO 与站内搜索 | 关键词聚合、sitemap 全套（news/pages/tools）、robots 模板 |
| 📊 质量门禁 | 每次更新前自动跑回归测试 + 内容质量 / 敏感信息检查，不过关不发布 |
| 🌍 地址单一数据源 | 站点域名统一由根目录 `CNAME` 管理，一处修改处处生效 |

## 技术栈

| 层 | 技术选型 |
|---|---|
| 数据管道 | Python 3.10+（`feedparser`、`requests`、`beautifulsoup4`、`readability-lxml`、`trafilatura`） |
| AI 增强 | OpenRouter 上各家 LLM（摘要 / 长文 / 洗稿 / 每日快报 / 工具评分） |
| 静态站 | Hugo（extended，`--minify`），`site/layouts` 模板 + `site/data` 数据驱动 |
| 定时调度 | GitHub Actions `schedule`（默认）；或阿里云 ECS `crontab`（自托管） |
| 托管 | GitHub Pages（默认）；或阿里云 ECS + Nginx / OSS + CDN |

## 目录结构

```
.
├── CNAME                     # 站点地址唯一数据源(裸域名 / 裸 IP / 带协议均可)
├── data/                     # 数据管道产物(18 个 json,是"源")
├── scripts/                  # Python 数据管道(35 个模块,aggregate.py 为总编排)
│   ├── aggregate.py          #   四阶段流水线总入口
│   ├── site_config.py        #   从 CNAME 读取 host/url/base_url 的共享模块
│   ├── quality_gate.py       #   质量门禁(内容/链接/图标/数据新鲜度)
│   ├── sanitize_secrets.py   #   抓取数据敏感信息脱敏
│   ├── update_readme_links.py#   重刷 README 数据新鲜度与站点地址
│   └── requirements.txt      #   管道依赖
├── site/                     # Hugo 站点
│   ├── hugo.toml             #   站点配置(menu/baseURL/robots)
│   ├── content/              #   内容页 md(新闻/工具/模型/Agent 详情页)
│   ├── data/                 #   data/ 的镜像(Hugo 模板只从这里读)
│   ├── layouts/              #   模板(含 seo.html、robots.txt 模板)
│   ├── static/               #   sitemap、favicon、图标库等
│   └── public/               #   构建产物(不提交,gitignore)
├── docs/                     # 部署/开发/设计等文档(见文末索引)
├── tests/                    # 回归测试(unittest,8 个文件)
└── .github/workflows/        # aggregate.yml(定时采集) + deploy.yml(发布)
```

## 数据管道四阶段流水线

总入口 `scripts/aggregate.py`，按 **采集 → 处理 → AI 增强 → 同步部署** 四阶段串行执行 30+ 步骤；每步独立 `try/except`，**单步失败不影响其余步骤**（"AI 增强挂了，今天的榜照样能出"），成败全部记录到 `data/meta.json` 的 `results` 字段 —— 排查问题先看它：

```bash
python -c "import json;print(json.load(open('data/meta.json'))['results'])"
```

| 阶段 | 职责 | 代表模块 | 产物 |
|---|---|---|---|
| Phase 1 采集 | 从各上游源抓原始数据 | `news_rss` `news_api` `github_discover` `github_trending` `huggingface_discover` `keyword_collector` `agent_discover` | `news.json` `projects.json` `trending.json` `models.json` `keywords.json` `agents.json` |
| Phase 2 处理 | 纯本地清洗加工（不调 LLM） | `refine_models` `generate_curated_models` `generate_rising` `update_providers` `daily_spotlight` `link_checker` | `models_curated.json` `rising.json` `providers.json` `daily.json` `broken_links.json` |
| Phase 3 AI 增强 | 调 LLM 对 news 滚雪球式补全 | `ai_enhance` `news_content_extract` `news_article_enhance` `news_rewrite` | 回写 `news.json`；`briefing.json`；`tools.json` 评分 |
| Phase 4 同步部署 | 榜单 + 静态页 + 镜像 + sitemap | `trending_scorer` `enrich_hot_data` `generate_tool_pages` `generate_news_pages` `sync_to_site` `generate_sitemap` | `hot.json`；`site/content/**/*.md`；`site/data/`；`site/static/sitemap*.xml` |

数据流：`data/*.json`（源）→ `sync_to_site()` 镜像到 `site/data/` → Hugo 模板读取渲染。

> 上游源含 **RSS 新闻、新闻 API、GitHub 项目与趋势、HuggingFace 模型、SEO 关键词、AI Agent 发现** 等；抓取频率受限流保护，详见 `docs/PIPELINE_RATE_LIMIT.md`。

## Hugo 站点与构建

```bash
cd site && hugo --minify --baseURL "https://hot.kehao.info/"
```

- **baseURL 不必手写**：CI 与部署脚本会从根目录 `CNAME` 解析出 host 与协议后传入 `--baseURL`，并写入 `site/public/CNAME`。
- 站点数据全部来自 `site/data/`（`sync_to_site()` 的镜像），模板直接 `site.Data.*` 消费。
- 内容页（新闻/工具等）由管道生成 `md` 到 `site/content/`，Hugo 构建为 `目录/index.html` 结构。
- `layouts/robots.txt` 为模板（`enableRobotsTXT = true`），sitemap 地址跟随 `--baseURL`；`seo.html` 输出 canonical / og: / 结构化数据，同样使用 `.Site.BaseURL`，无硬编码域名。
- `site/public/` 为构建产物，不入库。

## 质量保障

每次发布前依次执行（GitHub Actions 与 ECS cron 同样遵循）：

```bash
python -m unittest discover -s tests -p 'test_*.py'   # 回归测试(8 个文件)
python scripts/sanitize_secrets.py --check            # 敏感信息扫描(抓取文本可能混入密钥)
python scripts/quality_gate.py                        # 质量门禁:数据新鲜度/中文化/图标合法性/链接/模板禁项
```

任一步失败即中止发布，站点保持上一次成功构建，绝不把"半成品"暴露上线。

## 本地快速开始

```bash
# 1. 克隆(公开仓库,HTTPS 即可,无需 SSH key/token)
git clone https://github.com/Kehao/hot.git && cd hot

# 2. Python 依赖(建议 venv)
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip          # 注意:Ubuntu 自带 pip 22.0.2 有 resolver bug,务必先升级
pip install -r scripts/requirements.txt

# 3. 跑全量数据管道(耗时较长,依赖网络与 LLM 配额)
python scripts/aggregate.py

# 4. 本地预览 Hugo 站(需先安装 hugo extended)
hugo server -s site -D --baseURL "http://localhost:1313/"

# 5. 只做质量校验(不改数据)
python scripts/quality_gate.py
```

> 只想调单个环节？每个模块都可独立运行，例如 `python scripts/generate_sitemap.py`、`python scripts/update_readme_links.py`；全链路编排见 `aggregate.py` 的步骤清单。

## 部署

### GitHub Actions 自动部署

两条工作流分工：

| 工作流 | 触发 | 做什么 |
|---|---|---|
| `aggregate.yml`（6-Hour AI Data Aggregation） | `schedule: 0 */6 * * *` 或手动 dispatch | 装依赖 → 回归测试 → 跑 `aggregate.py` → 脱敏 → 回归测试 → 质量门禁 → 自动 commit + push 数据/产物 |
| `deploy.yml`（Deploy to GitHub Pages） | push 到 main（涉及 site/data）、聚合成功后、或手动 | 刷新 meta 时间 → `data/` 同步到 `site/data/` → 密钥扫描 → **从 CNAME 解析 baseURL** → `hugo --minify` → 写 `public/CNAME` → 发布 gh-pages |

工作流联动：`aggregate.yml` 每 6h 产出新数据并推送 → 触发 `deploy.yml` 重新构建发布，全程闭环。

仓库开启 GitHub Pages（Source: gh-pages branch）并把 `CNAME` 指向你的域名即可。

### 阿里云自托管方案

> 适用：希望管道在国内稳定执行、彻底不依赖 GitHub Actions、后续要加后端/数据库。
> 完整分步（含 ICP 备案、OSS 方案 A、成本对比）见 **`docs/ALIYUN_DEPLOYMENT.md`**，此处为速览。

```bash
# B1. 初始化:依赖 + Hugo
sudo apt update && sudo apt install -y python3 python3-pip nginx git rsync cron
#    安装 hugo extended 并放入 /usr/local/bin/

# B2. 拉代码(公开仓库用 HTTPS) + Python 依赖
sudo mkdir -p /var/www && sudo chown $USER /var/www
git clone https://github.com/Kehao/hot.git /var/www/hot
cd /var/www/hot && python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r scripts/requirements.txt

# B3. 配置 cron(见下节"crontab 生产实例",一行一个任务)
crontab -e

# B4. Nginx 托管发布目录
#     /etc/nginx/sites-available/hot → root /var/www/hot-www; server_name hot.kehao.info
sudo ln -s /etc/nginx/sites-available/hot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**生产目录约定**（原子发布，避免半成品暴露）：

```
/var/www/hot        # 仓库:代码 + 管道 + site/public(每次构建产物)
/var/www/hot-www    # Nginx root:由 rsync 从 site/public 镜像,只含"最后一次成功构建"
```

### 切换域名

根目录 `CNAME` 是全项目站点地址的**唯一数据源**，支持三种写法：

| CNAME 内容 | 解析结果（`scripts/site_config.py`） |
|---|---|
| `hot.kehao.info` | `https://hot.kehao.info`（域名默认 https） |
| `47.114.36.224`（裸 IP） | `http://47.114.36.224`（IP 默认无 TLS） |
| `https://hot.kehao.info`（带协议） | 尊重原协议 |

改域名只需改 `CNAME`，以下全部自动跟随（运行期读取，无硬编码）：

- 各 Python 脚本生成的链接与 README 站点地址（`site_config.py` → `generate_sitemap` / `enrich_hot_data` / `trending_scorer` / `update_readme_links` 等）
- Hugo 构建的 `--baseURL` 与 `public/CNAME`（`deploy.yml` 的 Resolve 步骤）
- favicon 黑名单 / 质量门禁（`site_config.favicon_fragments()`，历史域名进 `LEGACY_HOSTS` 持续识别）

## crontab 生产实例

> ⚠️ cron 规则是**一行一个任务、不能用 `\` 反斜杠续行**（会把第二行当成新任务而报 `bad minute`）。以下为经实战验证的**单行**写法：

```cron
# 每 6 小时:同步代码 → 聚合数据 → 脱敏 → 质量门禁 → Hugo 构建 → rsync 发布
0 */6 * * *  cd /var/www/hot && git fetch origin -q && git reset --hard origin/main -q && .venv/bin/python scripts/aggregate.py && .venv/bin/python scripts/sanitize_secrets.py && .venv/bin/python scripts/quality_gate.py && hugo --minify -s site && rsync -a --delete /var/www/hot/site/public/ /var/www/hot-www/ && echo "[$(date '+%F %T')] ok" >> /var/log/hot-cron.log || echo "[$(date '+%F %T')] FAILED" >> /var/log/hot-cron.log
```

| 片段 | 为什么这么写 |
|---|---|
| `git fetch + reset --hard origin/main` | `aggregate.py` 会改写本地 `data/*.json`，若用 `git pull` 会冲突；reset 以远端代码为准，数据由管道现场重新生成 |
| `.venv/bin/python` | 用绝对路径，避免 cron 的 PATH 找不到解释器 |
| `&&` 串行 | 任一步失败即中止（`||` 落 FAILED 日志），线上目录保持旧版可用 |
| `>> /var/log/hot-cron.log 2>&1` 风格 | 落盘审计；也可用示例中的 `echo ... ok/FAILED` 只记结果 |
| 首次验证 | `crontab -l` 查看已装任务；先手动执行一遍整条命令确认无错，再让 cron 接管 |

> 服务器上也可把以上命令封装成 `/usr/local/bin/hot-deploy.sh`（见 `scripts/aggregate.py` 头部说明），crontab 只留一行 `0 */6 * * * /usr/local/bin/hot-deploy.sh`。

## 实战踩坑记录

| 现象 | 根因 | 解法 |
|---|---|---|
| `git@github.com: Permission denied (publickey)` | 服务器没有 GitHub SSH key | 公开仓库直接用 **HTTPS clone**，免 key/token |
| `AssertionError: Candidate is not for this requirement lxml[html-clean,...]` | Ubuntu 自带 pip 22.0.2 的 resolver bug | `pip install --upgrade pip` 后再装依赖 |
| `crontab: ...:26: bad minute` | 任务用 `\` 折成多行，cron 不认 | 整条命令合并为**单行** |
| `Failed to reload ngin.service: not found` | 拼写少了 `x` | `sudo systemctl reload nginx`；先 `sudo nginx -t` 校验 |
| `git pull` 频繁冲突 | `aggregate.py` 改写本地 `data/*.json` | 改用 `git fetch && git reset --hard origin/main` |
| `quality_gate` 超时被杀 | 遍历数千新闻页做中文校验，低配 ECS（1.6G 无 swap）内存/时间吃紧 | 见 `docs/PIPELINE_RATE_LIMIT.md`：限制抓取并发与单轮处理量 |
| 管道产物里混入旧域名 | 历史硬编码站点地址 | 已统一为 `CNAME` 单源 + `LEGACY_HOSTS` 兜底识别 |

## 相关文档

| 文档 | 内容 |
|---|---|
| `docs/ALIYUN_DEPLOYMENT.md` | 阿里云部署完整方案：方案 A（OSS+CDN）、方案 B（ECS+Nginx+cron）、ICP 备案、域名解析、迁移清单 |
| `docs/PIPELINE_RATE_LIMIT.md` | 管道限流与稳定性方案（低配 ECS 下的抓取并发控制） |
| `docs/SOURCE_CODE_GUIDE.md` | 30 分钟读懂源码：数据从哪来、到哪去 |
| `docs/V4_COMPLETE_REPORT.md` / `V4_DEVELOPMENT_PLAN.md` | v4.0 完成报告与开发计划 |
| `docs/HUGO_REDESIGN_PLAN.md` | 整站视觉改造方案 |
| `docs/UX_DESIGN_REVIEW_v4.md` / `DEEP_REVIEW_REPORT.md` | 体验/设计评估报告 |
| `docs/V3_DEVELOPMENT_GUIDE.md` / `DEEP_ANALYSIS_REPORT_v3.md` / `REPORT_v2.1.md` | v3.0 开发指南、深度分析、v2.1 测试报告（历史版本） |

---

## License

[MIT](LICENSE)

© AI热榜 · 数据与站点每 6 小时自动更新
