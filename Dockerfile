# 基础镜像走国内仓库，可用 --build-arg BASE_IMAGE=... 覆盖
ARG BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm
FROM ${BASE_IMAGE}

# Debian 源换清华（实测比阿里云快 6-7 倍）
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g; s|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# 不装 chromium-driver：DrissionPage 直接走 CDP，用不到 chromedriver
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl xvfb xauth chromium \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install requests DrissionPage

WORKDIR /app
COPY dpdns_renew.py /app/dpdns_renew.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV EMAIL="" PASSWORD="" DOMAIN="" \
    DRY_RUN="false" AUTO_MODE="false" \
    TZ=Asia/Shanghai DISPLAY=:99

ENTRYPOINT ["/app/entrypoint.sh"]
