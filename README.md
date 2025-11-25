# TokenGate — LLM Cost-Control Proxy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://hub.docker.com)
[![Tests](https://img.shields.io/badge/tests-25%20passing-success.svg)](./tests)

TokenGate is a lightweight, self-hosted reverse proxy that enforces per-session spending limits on LLM API usage. It prevents uncontrolled agent loops (e.g., LangGraph, LangChain) from generating excessive OpenAI charges by intercepting requests before they reach the LLM provider.

> **Available on Docker Hub**: Coming soon at `docker pull yourusername/tokengate`  
> **Source Code**: [GitHub Repository](https://github.com/yourusername/tokengateway)

## Features

### Core Features
- **Budget Enforcement**: Per-session spending limits with Redis-backed tracking
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI API endpoints
- **Cost Estimation**: Pre-request cost estimation and post-request accurate cost calculation
- **Structured Logging**: JSON-formatted logs for full audit trail
- **Docker Deployment**: Easy containerized deployment with Redis
- **Low Overhead**: <50ms overhead per request

### Phase 2 Features
- **Anomaly Detection**: Automatic detection of loops, rate limit violations, and spending velocity anomalies
- **CLI Management Tool**: Command-line interface for budget operations and session management
- **Web Dashboard**: Real-time monitoring dashboard with visual budgettracking and session management

## Quick Start

### Option 1: Using Docker Hub (Easiest)

```bash
# 1. Create configuration
cat > .env << EOF
OPENAI_API_KEY=your-openai-api-key-here
DEFAULT_BUDGET=10.00
LOG_LEVEL=INFO
EOF

# 2. Run TokenGate + Redis
docker network create tokengate-net

docker run -d --name redis \
  --network tokengate-net \
  redis:7-alpine

docker run -d --name tokengate \
  --network tokengate-net \
  -p 8000:8000 \
  --env-file .env \
  -e REDIS_URL=redis://redis:6379 \
  yourusername/tokengate:latest

# 3. Verify it's running
curl http://localhost:8000/health
```

### Option 2: Using Docker Compose (Recommended)

```bash
# 1. Download docker-compose.yml
curl -O https://raw.githubusercontent.com/yourusername/tokengateway/main/docker-compose.yml

# 2. Create .env file
cat > .env << EOF
OPENAI_API_KEY=your-openai-api-key-here
DEFAULT_BUDGET=10.00
LOG_LEVEL=INFO
EOF

# 3. Start services
docker-compose up -d

# 4. Check health
curl http://localhost:8000/health
```

### Option 3: From Source (For Development)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/tokengateway.git
cd tokengateway

# 2. Create .env from example
cp .env.example .env
# Edit .env with your API key

# 3. Start with Docker Compose
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
```

## Configuration

TokenGate is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key (required) | - |
| `OPENAI_BASE_URL` | OpenAI API base URL | `https://api.openai.com/v1` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `DEFAULT_BUDGET` | Default budget per session (USD) | `10.00` |
| `STRICT_MODE` | Require session_id in all requests | `false` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## API Usage

TokenGate is a drop-in replacement for the OpenAI API. Simply change your base URL from `https://api.openai.com/v1` to `http://localhost:8000/v1`.

### Session ID

Each request must include a session identifier for budget tracking. You can provide it in two ways:

1. **Header (preferred)**: `X-Session-ID: my-session-123`
2. **Query parameter**: `?session_id=my-session-123`

If not provided and `STRICT_MODE=false`, requests will use the default session.

### Example: Chat Completions

```python
import openai

# Configure client to use TokenGate
client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy-key"  # TokenGate will use its configured key
)

# Make a request with session ID
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ],
    headers={"X-Session-ID": "my-workflow-123"}
)

print(response.choices[0].message.content)
```

### Example: Using curl

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session-123" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Example: Embeddings

```python
response = client.embeddings.create(
    model="text-embedding-ada-002",
    input="The quick brown fox",
    headers={"X-Session-ID": "my-session-123"}
)
```

## Budget Management

### Setting Budgets

Budgets are managed per session. By default, each session starts with the `DEFAULT_BUDGET`. You can set custom budgets programmatically using the budget manager (see code examples) or by directly interacting with Redis.

### Budget Exceeded Response

When a request would exceed the session budget, TokenGate returns a `429 Too Many Requests` response:

```json
{
  "error": {
    "message": "Budget exceeded. Remaining: $2.50, Required: $5.00",
    "type": "insufficient_quota",
    "budget_info": {
      "budget": 10.00,
      "spent": 7.50,
      "remaining": 2.50
    }
  }
}
```

## Supported Endpoints

### API Endpoints
- `POST /v1/chat/completions` - Chat completions
- `POST /v1/embeddings` - Text embeddings
- `POST /v1/completions` - Legacy completions endpoint
- `GET /health` - Health check endpoint

### Dashboard Endpoints
- `GET /dashboard` - Web monitoring dashboard
- `GET /api/dashboard/sessions` - Get all sessions (JSON)
- `GET /api/dashboard/stats` - Get system statistics
- `POST /api/dashboard/session/{id}/reset` - Reset session
- `POST /api/dashboard/session/{id}/unfreeze` - Unfreeze session

## Local Development

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Redis:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

3. Create `.env` file (see Configuration section)

4. Run the application:
```bash
uvicorn src.main:app --reload
```

### Running Tests

```bash
pytest
```

## Architecture

TokenGate follows this request flow:

1. **Request Received**: FastAPI receives OpenAI-compatible request
2. **Session Extraction**: Extract `session_id` from header or query param
3. **Cost Estimation**: Estimate request cost using model pricing tables
4. **Budget Check**: Verify session has sufficient budget (Redis)
5. **Request Forwarding**: If approved, forward to OpenAI API
6. **Cost Calculation**: Calculate actual cost from response usage
7. **Budget Deduction**: Deduct actual cost from session budget (Redis)
8. **Response Return**: Return OpenAI response to client

## Logging

TokenGate outputs structured JSON logs with the following fields:

- `timestamp`: ISO 8601 timestamp
- `session_id`: Session identifier
- `model`: Model name used
- `estimated_cost`: Pre-request cost estimate
- `actual_cost`: Post-request actual cost
- `input_tokens`: Input tokens used
- `output_tokens`: Output tokens used
- `decision`: `allowed` or `blocked`
- `error`: Error message (if any)

Example log entry:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "session_id": "my-session-123",
  "model": "gpt-3.5-turbo",
  "estimated_cost": 0.0015,
  "actual_cost": 0.0012,
  "input_tokens": 10,
  "output_tokens": 5,
  "decision": "allowed"
}
```

## Pricing Tables

Model pricing is stored in `data/pricing_tables.json`. This file contains per-model pricing for input and output tokens. TokenGate automatically loads this file on startup.

To update pricing:
1. Edit `data/pricing_tables.json`
2. Restart the service

## Performance

- **Overhead**: <50ms per request
- **Throughput**: Supports 1,000+ requests/minute
- **Latency**: Minimal impact on request latency

## Troubleshooting

### Redis Connection Issues

If you see "Redis is not available" errors:
1. Verify Redis is running: `docker ps` or `redis-cli ping`
2. Check `REDIS_URL` environment variable
3. Ensure Redis is accessible from the TokenGate container

### Budget Not Enforcing

1. Check Redis is running and accessible
2. Verify session_id is being sent correctly
3. Check logs for budget check errors
4. Verify pricing table includes your model

### Requests Being Blocked

1. Check session budget: Use Redis CLI to inspect `session:{session_id}:budget` and `session:{session_id}:spent`
2. Verify cost estimates are reasonable
3. Check logs for budget exceeded messages

## Management Tools

### CLI Tool

TokenGate includes a powerful CLI for budget management:

```bash
# Set budget
python tokengate_cli.py set-budget my-session 25.00

# View budget
python tokengate_cli.py get-budget my-session

# List all sessions
python tokengate_cli.py list-sessions

# Freeze/unfreeze sessions
python tokengate_cli.py freeze-session my-session --reason "Suspicious activity"
python tokengate_cli.py unfreeze-session my-session
```

See [CLI.md](CLI.md) for complete documentation.

### Web Dashboard

Access the real-time monitoring dashboard at `http://localhost:8000/dashboard`:

- View all active sessions
- Monitor budget usage with visual indicators
- Manage frozen sessions
- System-wide statistics
- Auto-refresh every 10 seconds

See [DASHBOARD.md](DASHBOARD.md) for complete documentation.

## Anomaly Detection

TokenGate automatically detects and blocks suspicious patterns:

- **Rate Limiting**: Block sessions exceeding request limits
- **Loop Detection**: Identify identical consecutive requests
- **Velocity Monitoring**: Track spending rate per minute
- **Automatic Freezing**: Temporarily block anomalous sessions

Frozen sessions can be reviewed and unfrozen via CLI or dashboard.

## Documentation

- [Quick Start](README.md) - This file
- [Production Deployment](DEPLOYMENT.md) - Deployment guide for production
- [CLI Tool](CLI.md) - Command-line management tool documentation
- [Dashboard](DASHBOARD.md) - Web dashboard user guide
- [Changelog](CHANGELOG.md) - Version history and changes

## Project Structure

```
tokengateway/
├── src/                    # Application source code
│   ├── proxy/             # Request forwarding logic
│   ├── budget/            # Budget management
│   ├── pricing/           # Cost calculation
│   ├── anomaly/           # Anomaly detection
│   ├── dashboard/         # Web dashboard
│   ├── config/            # Configuration
│   └── utils/             # Utilities
├── tests/                 # Unit tests
├── data/                  # Pricing tables
├── tokengate_cli.py       # CLI tool
├── Dockerfile             # Container definition
├── docker-compose.yml     # Local deployment
└── requirements.txt       # Python dependencies
```

## Installation Options

### 🐳 Docker Hub (Production)
```bash
docker pull yourusername/tokengate:latest
```
- ✅ Pre-built and tested
- ✅ Multi-platform (AMD64, ARM64)
- ✅ Automatic updates with `:latest` tag
- ✅ Fast deployment

### 📦 GitHub (Development)
```bash
git clone https://github.com/yourusername/tokengateway.git
```
- ✅ Full source code access
- ✅ Customize and extend
- ✅ Contribute improvements
- ✅ Build from source

## Docker Hub

TokenGate is available as a Docker image for easy deployment:

**Image**: `yourusername/tokengate`  
**Tags**: `latest`, `1.0.0`, `1.0`, `1`  
**Platforms**: `linux/amd64`, `linux/arm64`

```bash
# Pull the image
docker pull yourusername/tokengate:latest

# Run with environment variables
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e REDIS_URL=redis://your-redis:6379 \
  yourusername/tokengate:latest
```

See [DOCKER_RELEASE.md](DOCKER_RELEASE.md) for publishing instructions.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/tokengateway/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/tokengateway/discussions)
- **Documentation**: Check the documentation files in this repo
- **Logs**: Review structured JSON logs for debugging

## Community

- ⭐ Star this repo if you find it useful
- 🐛 Report bugs via GitHub Issues
- 💡 Request features via GitHub Discussions
- 🤝 Contribute via Pull Requests

## Roadmap

Future enhancements:
- Support for Anthropic Claude API
- Support for Google Gemini API
- Prometheus metrics export
- Advanced analytics dashboard
- Budget alert notifications
- Scheduled budget resets

---

**Made with ❤️ for the AI community**

