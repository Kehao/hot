# direction-approved · 方向选定记录

> huashu-design Gate文件 · 三方向硬门实物化。任一授权语气不豁免本文件。

## 三方向初稿（已展示）

| 方向 | 取材逻辑 | 文件 | 截图 |
|---|---|---|---|
| **A · 暖纸编辑志** | 风格轮盘 · 网页库 12 号（warm editorial） | `direction-a-warm-editorial.html` | `shot-a.png` |
| **B · 撞色信息流** | 现实参照 · The Verge 2022 redesign | `direction-b-verge-brutalism.html` | `shot-b.png` |
| **C · 瑞士网格 · 品牌橙** | 最佳设计师定制 · Pentagram × 数据终端 | `direction-c-swiss-grid.html` | `shot-c.png` |

截图时机：2026-09-07 23:00 · Chrome headless `--window-size=1440,1700`
三版骨架互异、深浅覆盖（A 浅编辑 / B 撞色 / C 浅 Swiss）、反 AI-slop 各有侧重。

## 用户选择原话

> 用户在 2026-09-07 三方向展示后，选定 **方向 C · 瑞士网格 · 品牌橙**。
> 用户对「载体范围」与「基调」的前置选择：当前 Hugo 站直接改 · 深浅都出一版 → C 落在浅色一侧。

## 方向 C 设计要点（落地依据）

- **配色**：白底 `#FFFFFF` + 黑 `#0B0B0D` + 单一品牌橙 `#FF6B35`（继承站点 logo 资产）；涨跌绿 `#0F6E56` / 红 `#A32D2D` 仅用于数字
- **字体**：无衬线 display `-apple-system / PingFang SC / Noto Sans CJK SC` + 等宽数字 `SF Mono / Menlo`（tabular-nums 数字对位）
- **骨架**：1px 规则线分栏 + 等宽数字编号榜单 + 顶部三段 meta 条 + 编辑部版头
- **反 slop 表现**：白底+纯黑+单 brand accent，不用 #0D1117 偷懒解，不用 emoji 作图标，保留 logo 图片作为品牌锚点

## 落地阶段（主干执行 · Phase 6）

- [ ] baseof.html 全局 design tokens（颜色/字体/间距变量）+ 替换现 baseof 内联 GitHub-dark CSS
- [ ] index.html 首页改造（masthead + 大标题 hero + 三段 meta + 三栏列表 + 工具 grid + 模型 table）
- [ ] _default/list.html 列表风格统一
- [ ] _default/tool.html 工具详情页骨架
- [ ] _default/search.html 搜索页风格统一
- [ ] news/single.html 单篇新闻风格统一
- [ ] 404 / partials/seo.html 收尾
- [ ] 移动端适配
- [ ] 质量门禁 + 视觉走查（人工 + Playwright 截图对照）

> ⚠️ 用户约束：**未经指令不构建**。每阶段完成后不自动 `hugo` 构建，等用户提示再构建验证。

---
写于 2026-09-07 · huashu-design v2026.x · alchaincyf