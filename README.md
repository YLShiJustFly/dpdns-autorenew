# DPDNS Auto Renew

[English](README.md) | [中文](README_CN.md)

Automatic renewal for DigitalPlat DPDNS free domains. Logs in with a real browser
(Cloudflare Turnstile), then talks to the panel's own JSON API to check and renew.

## Features

- Real browser login through Cloudflare Turnstile (DrissionPage + Xvfb)
- Handles the panel's CSRF double-submit (`panel_csrf_token` + `X-CSRF-Token`)
- Reuses the saved session (valid ~5 days), only opens a browser when needed
- Pins Cloudflare challenge hosts to IPv4, so containers without IPv6 don't hang
- Checks `free_renewal.available` before renewing — safe to run on a schedule
- `DRY_RUN` mode for a no-op check

## Requirements

- Docker & Docker Compose

## Quick Start

```bash
git clone https://github.com/YLShiJustFly/dpdns-autorenew.git
cd dpdns-autorenew
cp .env.example .env
```

Edit `.env`:

```dotenv
DPDNS_EMAIL=you@example.com
DPDNS_PASSWORD=your_password
DPDNS_DOMAIN=yourdomain.dpdns.org
DRY_RUN=true
BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm
```

Credentials live in `.env` only — never in `docker-compose.yml`, never in git.

Build and do a dry run first:

```bash
docker compose build
docker compose run --rm dpdns-renew     # DRY_RUN=true: check only
```

Then set `DRY_RUN=false` and run it for real:

```bash
docker compose run --rm dpdns-renew
```

## Scheduling

Free renewal opens 120 days before expiry. Running daily is harmless — the
script exits early when the window is closed.

```cron
0 3 * * * cd /path/to/dpdns-autorenew && docker compose run --rm dpdns-renew >> renew.log 2>&1
```

## Files

```
dpdns-autorenew/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── dpdns_renew.py          # main script
├── .env.example
├── config/                 # runtime: session cookies, screenshots (gitignored)
├── README.md
└── README_CN.md
```

## Troubleshooting

**`failed to resolve source metadata for docker.io/...` / IPv6 i/o timeout**
Docker Hub is unreachable or resolves to IPv6. The default `BASE_IMAGE` points at
a China mirror. To pick a faster one:

```bash
for m in docker.m.daocloud.io docker.1ms.run docker.1panel.live hub.rat.dev; do
  echo -n "$m: "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 "https://$m/v2/"
done
```

`401` is normal for a registry. Then set `BASE_IMAGE` in `.env`.

**`xvfb-run: error: xauth command not found`**
`xauth` is only a Recommends of `xvfb`. The Dockerfile installs it explicitly.

**Stuck at “waiting for Turnstile”**
The container likely has no IPv6 route and Chrome picked an AAAA record for
`challenges.cloudflare.com`. The script resolves IPv4 and injects
`--host-resolver-rules` at browser start.

**`Incorrect email or password` with correct credentials**
Check `.env` for a trailing `\r` (Windows editors) or stray quotes:

```bash
grep PASSWORD .env | cat -A
sed -i 's/\r$//' .env
```

**Build is slow in China**
The apt step pulls Chromium and its dependencies (several hundred MB), but it is
cached after the first successful build. Tsinghua mirrors measured faster than
Aliyun; adjust the `sed` line in the Dockerfile if yours differ.

## License

MIT License
