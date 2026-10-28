# DPDNS 自动续期

[English](README.md) | [中文](README_CN.md)

DigitalPlat DPDNS 免费域名自动续期。用真实浏览器登录（过 Cloudflare Turnstile），
再调用面板自己的 JSON API 检查并续期。

## 特性

- 真实浏览器登录，过 Cloudflare Turnstile（DrissionPage + Xvfb）
- 处理面板的 CSRF 双提交（`panel_csrf_token` + `X-CSRF-Token`）
- 复用已保存的会话（约 5 天有效），只有失效时才重启浏览器
- 把 Cloudflare 挑战域名钉到 IPv4，容器没有 IPv6 也不会卡死
- 先看 `free_renewal.available` 再续期，可以放心每天跑
- 支持 `DRY_RUN` 空跑检查

## 环境要求

- Docker & Docker Compose

## 快速开始

```bash
git clone https://github.com/YLShiJustFly/dpdns-autorenew.git
cd dpdns-autorenew
cp .env.example .env
```

编辑 `.env`：

```dotenv
DPDNS_EMAIL=you@example.com
DPDNS_PASSWORD=your_password
DPDNS_DOMAIN=yourdomain.dpdns.org
DRY_RUN=true
BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm
```

账号密码只放 `.env`，不要写进 `docker-compose.yml`，不要提交到 git。

先构建 + 空跑：

```bash
docker compose build
docker compose run --rm dpdns-renew     # DRY_RUN=true：只检查不续期
```

确认无误后把 `DRY_RUN=false`，正式跑：

```bash
docker compose run --rm dpdns-renew
```

## 定时执行

免费续期窗口在到期前 120 天开放。每天跑没有副作用——窗口没开时脚本直接退出。

```cron
0 3 * * * cd /path/to/dpdns-autorenew && docker compose run --rm dpdns-renew >> renew.log 2>&1
```

## 文件结构

```
dpdns-autorenew/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── dpdns_renew.py          # 主脚本
├── .env.example
├── config/                 # 运行态：会话 cookie、截图（已 gitignore）
├── README.md
└── README_CN.md
```

## 常见问题

**`failed to resolve source metadata for docker.io/...` / IPv6 i/o timeout**
Docker Hub 拉不动，或解析到了 IPv6。默认 `BASE_IMAGE` 已指向国内镜像。
测哪个快：

```bash
for m in docker.m.daocloud.io docker.1ms.run docker.1panel.live hub.rat.dev; do
  echo -n "$m: "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 "https://$m/v2/"
done
```

registry 返回 `401` 是正常的。然后把能用的写进 `.env` 的 `BASE_IMAGE`。

**`xvfb-run: error: xauth command not found`**
`xauth` 只是 `xvfb` 的 Recommends，Dockerfile 里已显式安装。

**卡在「等待 Turnstile」**
容器多半没有 IPv6 出口，Chrome 优先用了 `challenges.cloudflare.com` 的 AAAA 记录。
脚本启动浏览器时会解析 IPv4 并注入 `--host-resolver-rules`。

**密码正确却报 `Incorrect email or password`**
检查 `.env` 是否有 `\r`（Windows 编辑器）或多余引号：

```bash
grep PASSWORD .env | cat -A
sed -i 's/\r$//' .env
```

**国内构建慢**
apt 那步要装 Chromium 及依赖（几百 MB），首次构建慢，成功后会被 Docker 缓存。
实测清华源比阿里云快，想换就改 Dockerfile 里那行 `sed`。

## 许可证

MIT License
