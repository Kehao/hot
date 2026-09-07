# hot.kehao.info 整站视觉改造方案

> 目标载体：**当前 Hugo 静态站**（`site/layouts` 模板 + 全局样式系统）
> 视觉方向：**huashu-design 三方向硬门·选定 C · 瑞士网格 + 单一品牌橙**
> 日期：2026-09-07 · 设计稿：`/design-demos/direction-c-swiss-grid.html` + `shot-c.png`
> Gate 文件：`/design-demos/direction-approved.md`

---

## 一、背景与现状

当前站点为 Hugo 静态站 + Python 数据管道：

- 模板：11 个 html 文件，全部内联 CSS/JS（约 2200 行），无构建、无组件、无路由框架
- 主题：深色 `#0d1117` + 橙色 accent `#ff6b35` —— 被 huashu-design 的反 AI-slop 清单**直接命中**（「均匀深蓝底 + 通用青/紫霓虹 glow = GitHub-dark 偷懒解」）
- 导航图标全部用 emoji（🔥🧠🛠️🤖📰🏢）—— 同被反 slop 列为「emoji 作图标 = slop」
- 内容侧真实数据完整：18 个 json、3860 条新闻、171 个工具、62 个模型——无需重做数据层

改造范围锁定为 **site/layouts 模板 + 全局 CSS 系统**，Python 数据管道与生成脚本**保持不动**。

---

## 二、设计 tokens · 方向 C

### 2.1 颜色（继承站点 logo 资产作为唯一 brand accent）

```css
:root {
  /* 基础面 */
  --bg:        #FFFFFF;   /* 页面底色 */
  --surface:   #FAFAF8;   /* 卡片/侧栏次底 */
  --ink:       #0B0B0D;   /* 主要文字 */
  --ink-2:     #6B6B70;   /* 次要文字 */
  --ink-3:     #B0B0B5;   /* 占位/禁用 */
  --hair:      rgba(11,11,13,.18); /* 1px 规则线 */
  --rule:      #0B0B0D;   /* 强调规则线 */

  /* 单一 brand accent（从 logo 火焰色取的橙色） */
  --brand:     #FF6B35;
  --brand-2:   #E5561F;   /* hover / 强调 */

  /* 仅用于数字涨跌 */
  --up:        #0F6E56;
  --down:      #A32D2D;

  /* 不引入渐变、不引入其他色相 — */
}
```

**反 slop 校验**：无 `#0D1117`、无 `#7F77DD` 紫渐变、无 #5200FF 撞色 —— 配色对当前站点的 GitHub-dark 偷懒解做正向替换。

### 2.2 字体

```css
:root {
  --font-display: -apple-system, "PingFang SC", "Noto Sans CJK SC",
                  "Helvetica Neue", Inter, sans-serif;
  --font-serif:   "Noto Serif CJK SC", "Songti SC", Georgia, serif;
  --font-mono:    "SF Mono", Menlo, ui-monospace, monospace;
}
```

排版意图：
- **display / 正文 / UI** 用无衬线（清晰、现代、与中文黑体融洽）
- **不引入**纯英文 Inter 当 display（huashu 反 slop：`Inter/Roboto/system fonts 作 display = 烂大街`）
- **大数字与编号**强制 `font-mono` + `font-variant-numeric: tabular-nums`，榜单数字对位

字号阶（clamp 做响应式）：

| token | desktop | mobile | 用途 |
|---|---|---|---|
| `--fs-display` | clamp(64px, 6vw, 96px) | 48px | hero 大标题 |
| `--fs-h1` | 48px | 32px | 页面大标题 |
| `--fs-h2` | 32px | 24px | 模块标题 |
| `--fs-h3` | 20px | 18px | 卡片标题 |
| `--fs-h4` | 14px | 13px | 小标题 |
| `--fs-body` | 15px | 15px | 正文（≥14px 反 slop 硬底线） |
| `--fs-meta` | 12px | 12px | 元信息/标签（≥12px 硬底线） |
| `--fs-caption` | 11px | 11px | 极小标注（letter-spacing 上限） |

### 2.3 间距与栅格

```css
:root {
  --space-1: 4px;   --space-2: 8px;   --space-3: 12px;
  --space-4: 16px;  --space-5: 24px;  --space-6: 32px;
  --space-7: 48px;  --space-8: 64px;  --space-9: 96px;
  --container: 1280px;  /* 主体最大宽 */
  --gutter: 24px;       /* 移动端边距 */
}
```

栅格：12 列，gutter 24px，规则线 `var(--hair)` 分隔（瑞士网格传统）。**不使用任何圆角**——所有容器直角，营造工具/终端气质。

---

## 三、组件库

### 3.1 基础类（base 层 · baseof.html）

- `.container` · 最大宽 1280px，左右内边距 24/28px
- `.section` · 上下 padding 32-48px，bottom 1px 规则线
- `.kicker` · 11px、letter-spacing 0.32em、`var(--brand)`、uppercase
- `.meta-row` · 等宽数字 + 字符间距 0.18em uppercase 元信息行

### 3.2 导航（masthead）

- sticky 顶条 · 1px 底部规则线
- 三段式：左 logo+名 · 中主导航（去掉 emoji，改文字）· 右 meta 期号/总收录
- logo 真实引用 `site/static/logos/logo.png`
- 主导航激活态：下边框 1px `--brand`

### 3.3 列表

- 三栏带规则线分栏（首页热榜）
- 编号用 `font-mono` + `--brand` + `letter-spacing: 0.04em`
- 每行 1px `--hair` 虚线下边（参考方向 C 实测视觉）
- **无圆角、无卡片阴影、无左 border accent**

### 3.4 卡片（hero 大头条）

- 极简：1px 黑色顶部规则线 + 内部 padding 32px
- 大标题用 `--fs-display` + `font-weight: 700` + `letter-spacing: -0.04em`
- 标签 `kicker` 上方，meta `src/热度/日期` 下方，等宽小字

### 3.5 工具 grid

- 4 列横排 · 网格间 1px 规则线分（无圆角）
- 工具名 `--fs-h3` `font-weight: 600`
- 类目标签 `lab`（11px、letter-spacing、uppercase、`--brand`）
- 价格/描述用 `--fs-meta` + `--ink-2`

### 3.6 模型榜（table）

- 表格化榜单（方向 C 的核心母题）
- 表头：`th` 11px uppercase letter-spacing、底部 `--rule`
- 编号列：`font-mono` + `--brand` + 22px
- 类别列：11px uppercase letter-spacing、`--ink-2`
- 评分列：右对齐 `font-mono` + `--brand`

### 3.7 搜索框

- 1px 规则线包边 · 无圆角 · `--ink` 文字
- focus：边框 `--brand` + 1px，无 glow（反 slop 禁用 box-shadow glow）

### 3.8 标签 / 徽章

- inline-block · 11px · uppercase · 0.18em letter-spacing · 1px 规则线包边
- 不带填充色 / 不带 emoji · 仅文字

### 3.9 Footer

- 极简一行 · 左侧站点说明 · 右侧小色块 `--brand` 背景 + 黑字 tag（标注「方向 C · Swiss Grid」水印）
- 友情链接沿用现有（`claude-skills.bt199.com`）

---

## 四、页面改造顺序

按 huashu 检查点4节奏（尽早 show，等反馈再写组件）分**6 阶段**：

### 阶段 1 · 全局骨架（基线）⬅ 起点

**文件**：`site/layouts/_default/baseof.html`、`site/layouts/robots.txt`、`site/layouts/partials/seo.html`

- [ ] 把 baseof 的内联 `<style>` 系统替换为方向 C tokens（颜色/字体/间距 CSS 变量）
- [ ] masthead 三段式：logo（真实 img 引用）+ 主导航（去掉 emoji，改文字）+ meta 期号
- [ ] footer 沿用 C 风格
- [ ] 保留现有签到 JS（streak · localStorage），逻辑不变，DOM id 不变
- [ ] 验证：旧 index / list / tool / search / news 页面在新 baseof 下仍可访问（结构可能略乱但不应崩）

### 阶段 2 · 首页 hero 改造（最小可见效果）

**文件**：`site/layouts/index.html`

- [ ] 顶部 masthead 下新增 64px 大标题 hero：今日头版 kicker + 88px 主标题 + dek 副文
- [ ] meta-strip：4 段等宽数字（本期热点 / 新增工具 / GitHub Top / 模型数），中间 1px 规则线分隔
- [ ] 三栏热榜（news / trending / tools），规则线分栏，编号等宽 + brand 色
- [ ] 工具精选 4 列 grid（规则线分）
- [ ] 模型榜改写为 `<table>`（方向 C 的标志母题）
- [ ] 保留 index.html 现有的「🧭 新用户引导三卡」（改样式不改逻辑）

### 阶段 3 · 列表与详情

**文件**：
- `site/layouts/_default/list.html` · 列表页（/tools/, /models/, /agents/, /providers/, /news/ 通用）
- `site/layouts/_default/tool.html` · 工具详情
- `site/layouts/tools/single.html` · 工具详情实际渲染页（与 _default/tool.html 关系需厘清）
- `site/layouts/news/single.html` · 新闻详情

- [ ] list.html 三栏卡片（无圆角）+ 顶部 kicker + 1px 规则线
- [ ] tool.html 极简表格化（参数 / 价格 / 优缺点 / 替代）
- [ ] news 单页 顶部 masthead + 大标题 + 文章正文（仍可用 Markdown 渲染）

### 阶段 4 · 搜索与对比

**文件**：
- `site/layouts/_default/search.html` · 487 行内联 JS 的复杂页
- `site/layouts/_default/compare.html` · 170 行

- [ ] search 页面重构为表格化结果 + 等宽数字 + brand 编号
- [ ] compare 页面双列对照表 + 等宽评分
- [ ] 保留搜索高亮/建议/排序 JS 逻辑，仅 DOM/CSS 适配

### 阶段 5 · 404 / partials 收尾

**文件**：
- `site/layouts/404.html`
- `site/layouts/partials/seo.html`（注意 baseof 顶部 meta 注入）

- [ ] 404 极简一行 + 大标题
- [ ] seo partial 用 C tokens 重写（title/desc/og）

### 阶段 6 · 移动端 + 性能 + 反 slop 走查

- [ ] 响应式断点（<900px）下：导航折叠、表格转堆叠、hero 字号缩到 48px
- [ ] 全站 `font-size` 走查（≥14px 正文 / ≥12px 标签）
- [ ] Playwright 截图全 5 页对比 C 方向板一致性
- [ ] Lighthouse 性能与可访问性 ≥ 90
- [ ] 反 slop checklist 全过（见下节）

---

## 五、反 AI-slop 检查清单（每阶段必走）

> 摘自 huashu-design SKILL.md §6，落地到本项目的具体规避项：

- [ ] 无 `#0D1117` 均匀深蓝 + 霓虹 glow 组合（方向 C 已替换为白底）
- [ ] 无 emoji 作图标（导航全部改文字：`今日头版 / AI 工具 / 模型 / Agent / 新闻 / 提供商 / 搜索 / 对比`）
- [ ] 无圆角卡片 + 左 border accent（方向 C 全部直角、规则线分）
- [ ] 无紫色渐变背景
- [ ] 无 SVG 手画人脸 / 占位剪影
- [ ] 无 Inter/Roboto/system font 作 display（display 用 PingFang SC / Noto Sans CJK SC 等中文优化字体）
- [ ] 无 Lorem ipsum（方向 C demo 已用站内真实数据）
- [ ] logo 用真实 `site/static/logos/logo.png`，不重画
- [ ] 文案用「」引号不用 ""
- [ ] 装饰性 emoji 不出现（仅 brand 资产 logo）

---

## 六、验收标准

### 6.1 视觉对比

每页生成 Playwright 截图（Chrome headless `--window-size=1440,1700`），与 `design-demos/shot-c.png` 视觉气质一致：
- 白底 + 黑字 + 单一品牌橙
- 1px 规则线分栏 / 无卡片阴影
- 等宽数字编号
- 字体秩序感（display / h1-h4 / body / meta 四级对比清晰）

### 6.2 URL 结构 1:1 保留（SEO 底线）

| 当前 URL | 改造后 | 不变 |
|---|---|---|
| `/` | `/` | ✅ |
| `/tools/` | `/tools/` | ✅ |
| `/tools/<slug>/` | `/tools/<slug>/` | ✅ |
| `/models/` | `/models/` | ✅ |
| `/news/<id>/` | `/news/<id>/` | ✅ |
| `/agents/` | `/agents/` | ✅ |
| `/providers/<id>/` | `/providers/<id>/` | ✅ |
| `/search/?q=...` | `/search/?q=...` | ✅ |
| `/compare/?a=...&b=...` | `/compare/?a=...&b=...` | ✅ |

4400+ 已收录 URL **全部保持可访问**。

### 6.3 数据层

- Python 管道（`scripts/aggregate.py` 等 35 个）**不动**
- `data/*.json`（18 个）**不动**
- `generate_*_pages.py` 把 json 摊成 md 的中间产物**不动**（生成路径不变）
- 仅修改 `site/layouts/` 模板层与 CSS 系统

### 6.4 性能

- 首屏 CSS 内联（保留 baseof 现有结构），不引入外部字体 CDN（避免国内访问阻塞）
- 单 HTML ≤ 200KB（含样式）
- 图片用现有 `site/static/` 资源，不引外链

### 6.5 可访问性

- 文字对比度 ≥ 4.5:1（白底黑字 21:1 远超）
- 正文字号 ≥ 14px
- 标签字号 ≥ 12px
- 表单元素 focus 状态明显（1px `--brand` 边）

---

## 七、风险与决策点

| 风险 | 影响 | 缓解 |
|---|---|---|
| baseof.html 改造引发布局崩塌（其他模板仍用旧 class） | 中 | 阶段1后立即 hugo 构建 + 人工走查首页/列表/详情 |
| 现有 emoji 导航跨页面共享（baseof + 各模板独立 nav 区段） | 中 | 优先改 baseof 的主导航；各模板如有重复 nav 段保留旧路径，逐步替换 |
| search.html 487 行内联 JS 与新 DOM 结构耦合 | 中 | 阶段4专项处理；先验证骨架能用，逻辑后置 |
| Hugo 内联 `<style>` 体积膨胀（baseof 已有 ~260 行 CSS） | 低 | 控制变量与类名复用；可拆出 `_default/baseof.css` 但 Hugo 不直接支持，可保持内联 |
| 移动端断点适配缺失 | 中 | 阶段6统一补；先用 desktop 验证再适配 |

---

## 八、时间线与工作量

| 阶段 | 改动 | 工作量 |
|---|---|---|
| 1. 全局骨架 | baseof + seo | 0.5 天 |
| 2. 首页 hero | index.html | 1 天 |
| 3. 列表/详情 | list/tool/single | 1.5 天 |
| 4. 搜索/对比 | search/compare | 1 天 |
| 5. 404/partials | 404/seo | 0.3 天 |
| 6. 走查+适配 | mobile/lh/slop-check | 0.5 天 |
| **合计** | | **约 5 个 AI 密集工作日**（纯人力约 2-3 周） |

每阶段完成后**不自动构建**，等用户提示再 `hugo --minify` 构建验证。

---

## 九、参考与素材

- 风格方向：`design-demos/direction-c-swiss-grid.html` + `shot-c.png`
- Gate 文件：`design-demos/direction-approved.md`
- huashu-design SKILL：`~/.workbuddy/skills/huashu-design/SKILL.md`
- 风格库（参考 20 号）：`~/.workbuddy/skills/huashu-design/references/design-styles.md`
- 品牌 logo：`site/static/logos/logo.png`
- 现有模板：`site/layouts/`（11 个 html）
- 真实数据样本：`data/hot.json`、`data/tools.json`、`data/news.json`、`data/models_curated.json`、`data/trending.json`、`data/daily.json`

---

*写于 2026-09-07 · 等用户审阅签字后进入阶段 1。*