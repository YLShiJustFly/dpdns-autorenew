# DPDNS Auto Renewal - Using DrissionPage
FROM python:3.11-slim-bookworm

# Use domestic mirror sources (China)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    xvfb \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Use domestic PyPI mirror (Tsinghua)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir requests DrissionPage

# Set working directory
WORKDIR /app

# Copy scripts
COPY dpdns_renew_drission.py /app/
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Environment variables
ENV EMAIL=""
ENV PASSWORD=""
ENV DOMAIN=""
ENV AUTO_MODE="true"
ENV DISPLAY=:99

# Use custom entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
