# hot 项目阿里云部署方案

> 项目本质:**Hugo 静态站点**(构建产物 `site/public`)+ **Python 数据管道**(`scripts/aggregate.py` 每 6 小时抓取 AI 热点 → 生成 `data/*.json`)。
> 当前链路:GitHub Actions 定时聚合 → Hugo 构建 → gh-pages,域名 `aihot.bt199.com`。
>
> 部署到阿里云的核心问题有二:
> 1. **静态产物放哪**(替代 gh-pages);
> 2. **定时管道在哪跑**(替代 GitHub Actions schedule)。
>
> 日期:2026-09-04

---

## ⚠️ 前置条件:ICP 备案

阿里云国内资源(OSS 自定义域名、CDN、ECS 公网 IP)绑定域名 **必须 ICP 备案**,且域名需完成**阿里云实名认证**。

- 若 `bt199.com` 已在阿里云备案 → 只需在备案系统添加子域名 `aihot`(极快)。
- 若未备案 → 先去 [阿里云 ICP 备案控制台](https://beian.aliyun.com/) 办理,通常 1~2 周。
- 若不想等备案,OSS/ECS 只能用分配的临时域名访问(不适合对外正式服务)。

---

## 方案 A:OSS 静态托管 + CDN(轻量,推荐)

> 最接近 GitHub Pages 的替代:**管道仍留在 GitHub Actions**,构建后把 `site/public` 同步到 OSS。适合"想尽快上阿里云、不想自己养服务器"。

### A1. 开通 OSS 并创建 Bucket

1. 控制台 → 对象存储 OSS → 创建 Bucket:
   - 名称:`aihot`(需全局唯一,可加后缀如 `aihot-bucket`)
   - 地域:选**华东/华北**等离用户近的地域
   - 读写权限:**公共读**(网站是公开的)
2. Bucket 内开启 **静态网站托管**:默认首页 `index.html`,默认 404 页留空。
   - Hugo 输出为 `目录/index.html` 结构(如 `/news/abc/index.html`),与 OSS 目录默认首页机制天然兼容,无需改造链接。

### A2. 安装并配置 ossutil

从阿里云文档下载对应版本(版本号以官网为准):
<https://help.aliyun.com/zh/oss/developer-reference/install-ossutil>

```bash
# 以 macOS 为例(下载 ossutil v2 后):
chmod +x ossutil && sudo mv ossutil /usr/local/bin/
ossutil config        # 填入 AccessKey ID / Secret(建议用 RAM 子账号,仅授 OSS 权限)
```

### A3. 手动上传静态产物

```bash
cd /Users/qiukehao/ai/hot
hugo --minify -s site                    # 构建 site/public
ossutil cp -r -f site/public/ oss://aihot/
```

### A4. 改造 GitHub Actions:构建后自动同步 OSS(替代 gh-pages 步骤)

新增 `.github/workflows/deploy-aliyun.yml`(或改造现有 `deploy.yml`):

```yaml
name: Deploy to Aliyun OSS

on:
  push:
    branches: [main]
  workflow_run:
    workflows: ["6-Hour AI Data Aggregation"]
    types: [completed]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: 'latest'
          extended: true
      - name: Build
        working-directory: site
        run: hugo --minify
      - name: Sync to OSS
        uses: manyuanrong/oss-upload-action@master
        with:
          accessKeyId: ${{ secrets.ALIYUN_AK_ID }}
          accessKeySecret: ${{ secrets.ALIYUN_AK_SECRET }}
          bucket: aihot          # 你的 Bucket 名
          endpoint: oss-cn-hangzhou.aliyuncs.com
          localPath: site/public
```

> 在 GitHub 仓库 Settings → Secrets 添加 `ALIYUN_AK_ID` / `ALIYUN_AK_SECRET`。

### A5. 绑定域名 + CDN(可选但推荐)

1. **CDN 加速**:OSS 控制台 → 传输管理 → 域名管理 → 添加自定义域名 `aihot.bt199.com`,开通 CDN(国内访问快、有缓存)。
2. 去域名解析(DNS 服务商处,若域名在阿里云则直接在云解析 DNS 控制台):
   - 记录类型 `CNAME`,主机记录 `aihot`,指向 CDN/OSS 提供的 CNAME 地址。
3. CDN 配置:缓存规则建议 `text/html` 不缓存或 60s(新闻站要实时),`js/css/img` 缓存 1 天。

### 成本

- OSS 标准存储 + CDN 流量:月访问量不大时约 **几元 ~ 几十元/月**。

---

## 方案 B:ECS + Nginx + cron(完全自托管)

> 管道、构建、定时、托管**全部在阿里云 ECS 上跑**,彻底不依赖 GitHub Actions。适合希望数据管道国内稳定执行、后续要加数据库/后端接口的场景。

### B1. 购买 ECS

- 配置建议:**2 vCPU / 4GB** 起步(管道涉及抓取与解析,内存别低于 2G)。
- 系统:**Ubuntu 22.04 / Alibaba Cloud Linux 3**。
- 安全组放行:**22(SSH)、80(HTTP)、443(HTTPS)**。

### B2. 服务器初始化(一次性)

```bash
# 安装依赖
sudo apt update && sudo apt install -y python3 python3-pip nginx git rsync cron
# 安装 Hugo(官网拿 amd64 版本)
wget https://github.com/gohugoio/hugo/releases/download/v0.136.0/hugo_extended_0.136.0_linux-amd64.tar.gz
tar -xzf hugo_*.tar.gz && sudo mv hugo /usr/local/bin/

# 拉取代码(Kehao/hot 是公开仓库 → 用 HTTPS,无需 SSH key / token;pull 也不需要凭据)
sudo mkdir -p /var/www && sudo chown $USER /var/www
# 若之前 SSH clone 失败留下了空目录,先清掉:
sudo rm -rf /var/www/hot
git clone https://github.com/Kehao/hot.git /var/www/hot

# Python 依赖(建议 venv)
cd /var/www/hot
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
```

### B3. 配置定时管道(cron)

```bash
crontab -e
```

```cron
# 每 6 小时执行:同步代码 → 聚合数据 → 校验 → 构建 → 发布
# 注意:aggregate.py 会改写本地 data/*.json,故用 fetch+reset 以远端代码为准(丢弃本地数据改动,随后会重新生成)
0 */6 * * *  cd /var/www/hot && git fetch origin -q && git reset --hard origin/main -q \
  && .venv/bin/python scripts/aggregate.py \
  && .venv/bin/python scripts/sanitize_secrets.py \
  && .venv/bin/python scripts/quality_gate.py \
  && hugo --minify -s site \
  && rsync -a --delete /var/www/hot/site/public/ /var/www/hot-www/ \
  && echo "[$(date '+%F %T')] ok" >> /var/log/hot-cron.log \
  || echo "[$(date '+%F %T')] FAILED" >> /var/log/hot-cron.log
```

> 首次手动执行一遍验证:`bash -c '整条命令'`,再让 cron 接管。

### B4. 配置 Nginx

`/etc/nginx/sites-available/hot`:

```nginx
server {
    listen 80;
    server_name aihot.bt199.com;

    root /var/www/hot-www;
    index index.html;

    # 新闻站建议 html 短缓存,静态资源长缓存
    location / {
        try_files $uri $uri/ =404;
    }
    location ~* \.(css|js|png|jpg|svg|woff2)$ {
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/hot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### B5. 域名解析 + HTTPS(可选)

- 云解析 DNS 添加 A 记录:`aihot` → ECS 公网 IP。
- HTTPS:阿里云免费证书(SSL 证书控制台)或用 certbot,拿到证书后 Nginx 加 443 server 块。

### 成本

- 按量/包年 ECS:约 **50~150 元/月**(2c4g 包年更划算);可买抢占式实例进一步降本。

---

## 方案对比速览

| 维度 | A:OSS+CDN | B:ECS+Nginx |
|------|-----------|-------------|
| 架构 | 静态托管 + GitHub Actions 管道 | 全自托管 |
| 成本 | 几元~几十元/月 | 50~150 元/月 |
| 运维 | 几乎零运维 | 需自己升级/备份 |
| 管道位置 | GitHub(国内访问偶有波动) | ECS 本地 cron,稳定 |
| 扩展性 | 仅静态站 | 可加后端/数据库 |
| 推荐场景 | 快速迁移、纯静态新闻站 | 管道要稳、要长期演进 |

---

## 迁移后注意事项

1. **旧部署下线**:切域名到阿里云并验证无误后,再关停 gh-pages(仓库 Settings → Pages → 取消)及旧 DNS。
2. **CNAME 文件**:OSS/CDN 方案在 OSS 控制台配置域名即可,不需要仓库内 CNAME 文件;ECS 方案也不使用该文件(它只对 GitHub Pages 生效)。
3. **两套定时不要并存**:迁移后若管道还在 GitHub Actions 里跑,OSS 会被持续覆盖——方案 A 是有意保留,方案 B 记得删除 `.github/workflows/aggregate.yml` 的 schedule(或整个工作流)。
4. **密钥管理**:GitHub Actions 用 Secrets;ECS 上用 `.env` 且加入 `.gitignore`(已忽略),勿写死在代码里。
5. **站点地址统一由 `CNAME` 管理**(2026-09-04 起):仓库根 `CNAME` 文件是站点地址唯一数据源,支持裸域名 `aihot.bt199.com`、裸 IP `47.114.36.224` 或带协议 `https://…`。脚本(脚本内 URL、sitemap、README 生成)、质量门禁(favicon 黑名单)已改为运行时读取;Hugo 模板用 `.Site.BaseURL`。因此**构建时需按 CNAME 传入 baseURL**:
   ```bash
   # 在仓库根计算并传给 hugo(方案 B 的 cron 请加上)
   proto="https"; host=$(cat CNAME)
   case "$host" in http://*|https://*) proto="${host%%://*}"; host="${host#*://}";; esac
   host="${host%%/*}"; host="${host%/}"
   hugo --minify -s site --baseURL "${proto}://${host}/"
   ```
   GitHub Actions 的 `deploy.yml` 已内置该逻辑(`Resolve site host & base URL from CNAME` 步骤)。
