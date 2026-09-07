# hot 站点 pipeline 限流与稳定性方案

> 背景：ECS 实例 i-bp1dmqyivuxuiaenul6v（2 vCPU / 1.6G RAM / **无 swap**）
> 现象：2026-09-07 00:00 cron 全量流水线运行期间实例异常——云助手进程消失、nginx 收 TCP 但 TLS/HTTP 无响应，需重启恢复。
> 诊断：无 swap + 每 6h 整点抓取高峰（aggregate.py 全量采集 + AI 增强 + hugo 构建 4000+ 页面）→ 内存尖峰触发 **OOM killer 连杀关键进程**。

---

## 一、结论先行

pipeline 主链路是**串行**抓取（`aggregate.py` 无并发线程池），请求频控不是重点。
真正要做的是四件事：**加 swap 兜底 → 限制并发/优先级 → 配 OOM 保护 → cron 错峰 + 防重入**。

```
内存尖峰 = 1.6G 物理内存无缓冲(无swap)
        └─ OOM killer 无差别开杀 → nginx/云助手被杀 → 站点假死
修复方向:
  L1 swap 兜底      : 内存打满先落盘, 内核不轻易开杀
  L2 并发/优先级限流 : HUGO_NUMWORKERMULTIPLIER 降渲染并行、nice/ionice 让位
  L3 OOM 护栏       : 要杀先杀 pipeline 自己, 不碰 nginx/ssh/云助手
  L4 调度错峰+防重入 : 避开整点、flock 锁防手动/cron 撞车
```

---

## 二、L1 swap 兜底（首选，5 分钟见效，低风险）

```bash
# 1) 创建 2G swapfile
fallocate -l 2G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile

# 2) 持久化到 /etc/fstab
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 3) 降低 swap 使用倾向（默认 60，系统优先用物理内存）
sysctl -w vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.d/99-hot.conf

# 验证
free -m            # 应看到 Swap: 2047
cat /proc/sys/vm/swappiness   # 10
```

回滚：`swapoff /swapfile && rm /swapfile`，并从 fstab/sysctl.d 删除对应行。

---

## 三、L2 并发/优先级限流（改 /usr/local/bin/hot-deploy.sh）

当前构建行 `hugo --minify -s site` 会按 CPU 数并行渲染，1.6G 内存下建议限并发。
⚠️ **注意**：hugo CLI **没有** `--concurrency` 标志（2026-09-08 实测 v0.136 直接报 `unknown flag: --concurrency`，导致整轮构建失败）。限并发请用环境变量 `HUGO_NUMWORKERMULTIPLIER`（hugo 官方支持，乘 CPU 数决定渲染并行度，可设小数）：

```bash
HUGO_NUMWORKERMULTIPLIER=0.5 hugo --minify -s site   # 渲染并行度降为 CPU 的一半
```

抓取与构建阶段让出 CPU / IO，避免与 web 服务抢资源：

```bash
nice -n 10 ionice -c 3 .venv/bin/python scripts/aggregate.py
nice -n 10 ionice -c 3 hugo --minify -s site
```

> 若未来在代码里引入并发抓取，统一遵守：`requests.Session` + 连接池 `pool_maxsize=4` + 每请求 `time.sleep(0.5~1)` + 源级最低间隔，避免瞬时打爆内存与对方限流。

---

## 四、L3 OOM 护栏（要杀先杀 pipeline，不碰服务）

### A. 保护 nginx（推荐，drop-in 配置）

```bash
mkdir -p /etc/systemd/system/nginx.service.d
cat > /etc/systemd/system/nginx.service.d/oom.conf <<'EOF'
[Service]
OOMScoreAdjust=-800
EOF
systemctl daemon-reload
systemctl show nginx -p OOMScoreAdjust   # 应输出 -800
```

（云助手 aliyun-assist 一般自带较高保护，nginx 是关键业务，优先保它。）

### B. pipeline 自认"可牺牲"

`hot-deploy.sh` 开头（root 运行）追加，主动抬高自己 OOM 优先级，
OOM 时内核先杀流水线，不误伤 nginx/ssh：

```bash
echo 500 > /proc/$$/oom_score_adj 2>/dev/null || true
```

### C. （可选激进）systemd-run 内存硬顶

把重活关进独立 scope，超限只杀该 scope：

```bash
systemd-run --scope -p MemoryMax=1300M \
  /var/www/hot/.venv/bin/python /var/www/hot/scripts/aggregate.py
```

> MemoryMax 触顶 = 该进程组被内核杀掉（日志 `Memory cgroup out of memory`），nginx 等不受影响。
> 注意：脚本里各阶段是顺序执行，若整链都要管，建议把 aggregate 单独用此方式跑。

---

## 五、L4 调度错峰 + 防重入

### 错峰：避开 00/06/12/18 整点

```bash
# 当前(整点): 0 */6 * * * /usr/local/bin/hot-deploy.sh
# 改为固定 4 个时刻(02:00/08:00/14:00/20:00), 避开整点任务与流量高峰, 也便于白天更新
crontab -e
0 2,8,14,20 * * * /usr/local/bin/hot-deploy.sh >> /var/log/hot-cron.out 2>&1
```

### 防重入：flock 锁（防止手动触发与 cron 撞车跑两个实例）

把 cron 行与手动执行统一走锁：

```bash
0 2,8,14,20 * * * flock -n /var/run/hot-deploy.lock -c '/usr/local/bin/hot-deploy.sh >> /var/log/hot-cron.out 2>&1'
```

手动重跑用同样命令：`flock -n /var/run/hot-deploy.lock -c '/usr/local/bin/hot-deploy.sh'`
（`-n` 非阻塞：已在跑则立即退出，避免双实例抢内存。）

---

## 六、L5（可选）启动自检：内存不足先等不硬闯

`hot-deploy.sh` 在 `cd` 后加一段——可用内存过低时最多等 30 分钟再开始：

```bash
# 可用内存 < 200M 时等待, 最多 30 轮 x 60s
for i in $(seq 1 30); do
  avail=$(free -m | awk 'NR==2{print $7}')
  [ "$avail" -ge 200 ] && break
  log "warn: 可用内存仅 ${avail}M, 等待 60s ($i/30)"
  sleep 60
done
```

---

## 七、验证清单

| 检查 | 命令 | 期望 |
|---|---|---|
| swap 生效 | `free -m` | Swap 约 2047M |
| swappiness | `cat /proc/sys/vm/swappiness` | 10 |
| nginx OOM 保护 | `systemctl show nginx -p OOMScoreAdjust` | -800 |
| cron 错峰+锁 | `crontab -l` | `25 */6 * * * flock ...` |
| 手动跑通 | `flock -n /var/run/hot-deploy.lock -c '...'` | 日志出现 ok |
| 无 OOM 杀进程 | `dmesg -T \| grep -i 'oom\|killed process'` | 无新记录 |

> 观察下一轮整链运行：`free -m` 峰值应触顶后回落 swap，而 nginx/站点保持可用。

---

## 八、备注

- 所有改动都在服务器本机（/usr/local/bin/hot-deploy.sh、crontab、systemd、fstab），**不涉及 GitHub 提交**。
- 仓库代码（scripts/*.py）当前无需改动；未来若加并发抓取再按 L2 备注规范限流。
- 长期建议：实例升配到 2C4G（约 ¥50-90/月 视规格）可从根上消除内存焦虑，swap 方案是 0 成本过渡。

---

## 九、实施记录（2026-09-08）

已在服务器 i-bp1dmqyivuxuiaenul6v 全量落地并核验：

| 项 | 状态 | 核验结果 |
|---|---|---|
| L1 swap 2G + fstab + swappiness=10 | ✅ | `free -m` Swap 2047M，fstab 已持久化 |
| L2 hot-deploy.sh 限并发/让位 | ✅ | `bash -n` 通过，backup 在 /usr/local/bin/*.bak.* |
| L3 pipeline oom_score_adj=500 | ✅ | 脚本第 12 行 |
| L3 nginx OOMScoreAdjust=-800 | ✅ | `systemctl show nginx` 输出 -800 |
| L4 cron 错峰 + flock | ✅ | `0 2,8,14,20 * * * flock -n /var/run/hot-deploy.lock -c '...'` |

**踩坑记录二（重要）**：L2 初版给 hugo 误加了 `--concurrency 2`，但 **hugo CLI 无此标志**——01:49 验证轮整链构建失败
（`Error: unknown flag: --concurrency`，已 `sed` 移除恢复 `hugo --minify -s site`）。若确需限渲染并行度，用环境变量 `HUGO_NUMWORKERMULTIPLIER=0.5`。

**踩坑记录（重要）**：通过云助手（workbench exec）执行 `... | crontab -` 会装入**空** crontab——
云助手环境下命令 stdin 不可用，`crontab -` 读到 EOF 直接装了空表，把旧条目清掉了。
正确姿势：先把内容写到文件再 `crontab <file>`。若下次要改 cron，务必用文件方式。
旧表曾被误清，已用 `crontab /tmp/hot-cron.line` 恢复为新计划（下次触发 06:25）。
