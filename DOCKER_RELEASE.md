# Docker Hub Release Guide

This guide explains how to build and publish TokenGate to Docker Hub for easy distribution.

## Prerequisites

1. Docker Hub account (free at https://hub.docker.com)
2. Docker Desktop installed and running
3. Login to Docker Hub:
   ```bash
   docker login
   ```

## Building the Image

### 1. Build for Your Platform

```bash
# Build for local platform
docker build -t yourusername/tokengate:1.0.0 .
docker tag yourusername/tokengate:1.0.0 yourusername/tokengate:latest
```

### 2. Build Multi-Platform (Recommended)

Build for both AMD64 (x86) and ARM64 (Apple Silicon, Raspberry Pi):

```bash
# Create and use buildx builder
docker buildx create --name tokengate-builder --use

# Build and push multi-platform
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag yourusername/tokengate:1.0.0 \
  --tag yourusername/tokengate:latest \
  --push \
  .
```

## Pushing to Docker Hub

### Single Platform Push

```bash
docker push yourusername/tokengate:1.0.0
docker push yourusername/tokengate:latest
```

### Verify Upload

Check your Docker Hub repository at:
```
https://hub.docker.com/r/yourusername/tokengate
```

## Docker Hub Repository Setup

### 1. Create Repository

1. Go to https://hub.docker.com
2. Click "Create Repository"
3. Name: `tokengate`
4. Visibility: Public (or Private if preferred)
5. Description: "Self-hosted reverse proxy that enforces per-session spending limits on LLM API usage"

### 2. Add Repository Details

**Short Description:**
```
LLM Cost-Control Proxy - Enforce per-session spending limits on OpenAI API usage
```

**Full Description:**
```markdown
# TokenGate - LLM Cost-Control Proxy

TokenGate is a lightweight, self-hosted reverse proxy that enforces per-session spending limits on LLM API usage. Perfect for preventing runaway costs from AI agents and automated workflows.

## Features
- 💰 Per-session budget enforcement
- 🔄 OpenAI-compatible API (drop-in replacement)
- 🚨 Anomaly detection (loops, rate limits, spending velocity)
- 📊 Web dashboard for monitoring
- 🛠️ CLI management tool
- 📝 Structured JSON logging
- 🚀 Docker-ready with Redis included

## Quick Start

```bash
# 1. Create .env file
echo "OPENAI_API_KEY=your-key-here" > .env
echo "DEFAULT_BUDGET=10.00" >> .env

# 2. Run with Docker Compose
curl -O https://raw.githubusercontent.com/yourusername/tokengateway/main/docker-compose.yml
docker-compose up -d

# 3. Use TokenGate
curl http://localhost:8000/health
```

## Documentation
- GitHub: https://github.com/yourusername/tokengateway
- Docs: https://github.com/yourusername/tokengateway/blob/main/README.md

## Support
Report issues: https://github.com/yourusername/tokengateway/issues
```

### 3. Add Tags

Add relevant tags to your Docker Hub repo:
- `openai`
- `llm`
- `cost-control`
- `proxy`
- `fastapi`
- `redis`
- `python`

## Version Tags Strategy

Use semantic versioning:

```bash
# Major.Minor.Patch
docker tag yourusername/tokengate:1.0.0 yourusername/tokengate:1.0
docker tag yourusername/tokengate:1.0.0 yourusername/tokengate:1
docker tag yourusername/tokengate:1.0.0 yourusername/tokengate:latest

docker push yourusername/tokengate:1.0.0
docker push yourusername/tokengate:1.0
docker push yourusername/tokengate:1
docker push yourusername/tokengate:latest
```

This allows users to:
- Pin to exact version: `yourusername/tokengate:1.0.0`
- Stay on minor version: `yourusername/tokengate:1.0`
- Stay on major version: `yourusername/tokengate:1`
- Always get latest: `yourusername/tokengate:latest`

## Automated Builds (Optional)

### GitHub Actions + Docker Hub

Create `.github/workflows/docker-publish.yml`:

```yaml
name: Docker

on:
  release:
    types: [published]
  push:
    branches: [ main ]

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Log in to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: yourusername/tokengate
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

Add secrets to GitHub:
- `DOCKER_USERNAME`: Your Docker Hub username
- `DOCKER_PASSWORD`: Your Docker Hub access token

## Image Size Optimization

Current image size should be ~200-300MB. To optimize:

1. Use Alpine-based Python image
2. Remove build dependencies after installation
3. Use multi-stage builds
4. Minimize layers

## Testing the Published Image

```bash
# Pull your image
docker pull yourusername/tokengate:latest

# Test it works
docker run --rm \
  -e OPENAI_API_KEY=test-key \
  -p 8000:8000 \
  yourusername/tokengate:latest
```

## Security Scanning

Scan your image for vulnerabilities:

```bash
# Using Docker Scout
docker scout cves yourusername/tokengate:latest

# Using Trivy
trivy image yourusername/tokengate:latest
```

## Update README with Docker Hub Link

Add badge to your GitHub README:

```markdown
[![Docker Hub](https://img.shields.io/docker/v/yourusername/tokengate?label=Docker%20Hub)](https://hub.docker.com/r/yourusername/tokengate)
[![Docker Pulls](https://img.shields.io/docker/pulls/yourusername/tokengate)](https://hub.docker.com/r/yourusername/tokengate)
```

## Release Checklist

- [ ] Build multi-platform image
- [ ] Push all version tags
- [ ] Update Docker Hub description
- [ ] Test image pulls and runs
- [ ] Update GitHub README with Docker Hub links
- [ ] Create GitHub release with matching version
- [ ] Announce on social media/communities

## Troubleshooting

### Login Issues
```bash
docker logout
docker login
```

### Multi-platform Build Issues
```bash
docker buildx ls
docker buildx create --use
```

### Permission Issues
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in
```

---

For questions or issues, see: https://github.com/yourusername/tokengateway/issues

