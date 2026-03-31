# DPDNS Auto Renew

[English](README.md) | [中文](README_CN.md)

Automatic renewal tool for DigitalPlat DPDNS free domains using DrissionPage to bypass Cloudflare Turnstile verification.

## Features

- Automatic bypass of Cloudflare Turnstile CAPTCHA
- Cookie persistence
- Docker containerized deployment
- Support for scheduled execution via crontab

## Requirements

- Docker & Docker Compose
- Linux/Windows/MacOS with Docker support

## Quick Start

### 1. Clone or Download

```bash
git clone https://github.com/YLShiJustFly/dpdns-autorenew.git
cd dpdns-autorenew
```

Or download and extract the release package.

### 2. Configure Environment Variables

Edit `docker-compose.yml`:

```yaml
services:
  dpdns-renew:
    build: .
    container_name: dpdns-renew
    environment:
      - EMAIL=your_email@example.com      # Your DPDNS email
      - PASSWORD=your_password            # Your DPDNS password
      - DOMAIN=yourdomain.dpdns.org       # Your DPDNS domain
      - AUTO_MODE=false                   # Set to false for cron execution
      - TZ=Asia/Shanghai
      - DISPLAY=:99
    volumes:
      - ./config:/config
    shm_size: 2gb
```

### 3. Build and Run

```bash
# Build and start
docker compose up -d --build

# View logs
docker logs -f dpdns-renew
```

### 4. Set Up Scheduled Execution (Optional)

Edit crontab to run annually on October 1st:

```bash
crontab -e
```

Add the following line:

```
0 9 1 10 * cd /path/to/dpdns-renew && docker compose up -d
```

This will execute the renewal at 9:00 AM on October 1st every year.

## File Structure

```
dpdns-renew/
├── Dockerfile              # Docker build configuration
├── docker-compose.yml      # Docker Compose configuration
├── entrypoint.sh          # Container entry script
├── dpdns_renew_drission.py # Main renewal script
├── config/                # Persistent data directory
│   ├── .dpdns_cookies.json
│   └── *.png
└── README.md
```

## Troubleshooting

### Container keeps restarting
Set `AUTO_MODE=false` in `docker-compose.yml` and use crontab for scheduled execution instead.

### Slow build speed in China
The Dockerfile uses Aliyun mirror for APT and Tsinghua mirror for PyPI by default.

### Renewal failed
Check logs with `docker logs -f dpdns-renew`. The script will save screenshots in the `config/` directory for debugging.

## License

MIT License
