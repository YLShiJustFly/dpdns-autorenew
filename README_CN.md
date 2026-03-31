# DPDNS 自动续期

[English](README.md) | [中文](README_CN.md)

使用 DrissionPage 绕过 Cloudflare Turnstile 验证码的 DigitalPlat DPDNS 免费域名自动续期工具。

## 特性

- 自动绕过 Cloudflare Turnstile 人机验证
- Cookie 持久化
- Docker 容器化部署
- 支持 crontab 定时执行

## 环境要求

- Docker & Docker Compose
- 支持 Docker 的 Linux/Windows/MacOS

## 快速开始

### 1. 克隆或下载

```bash
git clone https://github.com/YLShiJustFly/dpdns-autorenew.git
cd dpdns-autorenew
```

或直接下载并解压发布包。

### 2. 配置环境变量

编辑 `docker-compose.yml`：

```yaml
services:
  dpdns-renew:
    build: .
    container_name: dpdns-renew
    environment:
      - EMAIL=your_email@example.com      # 你的 DPDNS 邮箱
      - PASSWORD=your_password            # 你的 DPDNS 密码
      - DOMAIN=yourdomain.dpdns.org       # 你的 DPDNS 域名
      - AUTO_MODE=false                   # 设为 false，使用 cron 定时执行
      - TZ=Asia/Shanghai
      - DISPLAY=:99
    volumes:
      - ./config:/config
    shm_size: 2gb
```

### 3. 构建并运行

```bash
# 构建并启动
docker compose up -d --build

# 查看日志
docker logs -f dpdns-renew
```

### 4. 设置定时执行（可选）

编辑 crontab，设置每年10月1日执行：

```bash
crontab -e
```

添加以下行：

```
0 9 1 10 * cd /path/to/dpdns-renew && docker compose up -d
```

这将在每年10月1日早上9点执行续期。

## 文件结构

```
dpdns-renew/
├── Dockerfile              # Docker 构建配置
├── docker-compose.yml      # Docker Compose 配置
├── entrypoint.sh          # 容器入口脚本
├── dpdns_renew_drission.py # 主续期脚本
├── config/                # 持久化数据目录
│   ├── .dpdns_cookies.json
│   └── *.png
└── README.md
```

## 常见问题

### 容器不断重启
在 `docker-compose.yml` 中设置 `AUTO_MODE=false`，改用 crontab 定时执行。

### 国内构建速度慢
Dockerfile 默认使用阿里云 APT 镜像和清华 PyPI 镜像。

### 续期失败
使用 `docker logs -f dpdns-renew` 查看日志。脚本会在 `config/` 目录保存截图用于调试。

## 许可证

MIT License
