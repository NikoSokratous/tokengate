# TokenGate CLI Documentation

The TokenGate CLI provides command-line management of budgets, sessions, and anomaly detection.

## Installation

The CLI is included with TokenGate. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python tokengate_cli.py [OPTIONS] COMMAND [ARGS]...
```

### Options

- `--redis-url TEXT`: Redis connection URL (default: `redis://localhost:6379`)
- `--help`: Show help message

## Commands

### set-budget

Set or update budget for a session.

```bash
python tokengate_cli.py set-budget SESSION_ID AMOUNT
```

**Examples:**
```bash
# Set budget of $25.50 for session "my-workflow"
python tokengate_cli.py set-budget my-workflow 25.50

# Set budget using custom Redis URL
python tokengate_cli.py --redis-url redis://prod-redis:6379 set-budget prod-session 100.00
```

### get-budget

Get budget information for a specific session.

```bash
python tokengate_cli.py get-budget SESSION_ID
```

**Example:**
```bash
python tokengate_cli.py get-budget my-workflow
```

**Output:**
```
Session: my-workflow
Budget:    $25.5000
Spent:     $12.3456
Remaining: $13.1544
Used:      48.4%
```

### list-sessions

List all active sessions with budget information.

```bash
python tokengate_cli.py list-sessions [--format table|json]
```

**Examples:**
```bash
# Table format (default)
python tokengate_cli.py list-sessions

# JSON format
python tokengate_cli.py list-sessions --format json
```

**Output (table):**
```
╔══════════════╦═══════════╦═══════════╦═══════════╦═════════╗
║ Session ID   ║ Budget    ║ Spent     ║ Remaining ║ Used %  ║
╠══════════════╬═══════════╬═══════════╬═══════════╬═════════╣
║ session-1    ║ $10.0000  ║ $2.3456   ║ $7.6544   ║ 23.5%   ║
║ session-2    ║ $25.0000  ║ $15.6789  ║ $9.3211   ║ 62.7%   ║
╚══════════════╩═══════════╩═══════════╩═══════════╩═════════╝
```

### reset-session

Reset budget and spending for a session (requires confirmation).

```bash
python tokengate_cli.py reset-session SESSION_ID
```

**Example:**
```bash
python tokengate_cli.py reset-session my-workflow
# Prompt: Are you sure you want to reset this session? [y/N]:
```

### freeze-session

Manually freeze a session for 1 hour.

```bash
python tokengate_cli.py freeze-session SESSION_ID [--reason TEXT]
```

**Examples:**
```bash
# Freeze with default reason
python tokengate_cli.py freeze-session suspicious-session

# Freeze with custom reason
python tokengate_cli.py freeze-session bot-session --reason "Bot detected"
```

### unfreeze-session

Unfreeze a previously frozen session.

```bash
python tokengate_cli.py unfreeze-session SESSION_ID
```

**Example:**
```bash
python tokengate_cli.py unfreeze-session suspicious-session
```

### anomaly-stats

Get anomaly detection statistics for a session.

```bash
python tokengate_cli.py anomaly-stats SESSION_ID
```

**Example:**
```bash
python tokengate_cli.py anomaly-stats my-session
```

**Output:**
```
Anomaly Stats for: my-session
Frozen: Yes
Reason: Loop detected: 5 identical consecutive requests
Requests (last minute): 87
```

### health

Check Redis connection health.

```bash
python tokengate_cli.py health
```

**Output:**
```
✓ Redis connection healthy
```

## Common Workflows

### Initial Setup

```bash
# Set budgets for multiple sessions
python tokengate_cli.py set-budget dev-team 50.00
python tokengate_cli.py set-budget staging 100.00
python tokengate_cli.py set-budget production 500.00
```

### Monitoring

```bash
# Check all sessions
python tokengate_cli.py list-sessions

# Check specific session
python tokengate_cli.py get-budget production

# Check for anomalies
python tokengate_cli.py anomaly-stats production
```

### Incident Response

```bash
# Freeze suspicious session
python tokengate_cli.py freeze-session bot-attack --reason "Unusual traffic pattern"

# Check anomaly stats
python tokengate_cli.py anomaly-stats bot-attack

# Later, unfreeze if false positive
python tokengate_cli.py unfreeze-session bot-attack
```

### Batch Operations

```bash
# Reset all sessions (bash script)
for session in $(python tokengate_cli.py list-sessions --format json | jq -r '.[].session_id'); do
    python tokengate_cli.py reset-session $session --yes
done
```

## Integration with Scripts

### Python Script Example

```python
import subprocess
import json

# Get all sessions as JSON
result = subprocess.run(
    ['python', 'tokengate_cli.py', 'list-sessions', '--format', 'json'],
    capture_output=True,
    text=True
)
sessions = json.loads(result.stdout)

# Alert if any session used > 90%
for session in sessions:
    if session['percentage_used'] > 90:
        print(f"Alert: {session['session_id']} at {session['percentage_used']:.1f}%")
```

### Bash Monitoring Script

```bash
#!/bin/bash
# monitor-budgets.sh

THRESHOLD=80

python tokengate_cli.py list-sessions --format json | \
    jq -r --arg threshold "$THRESHOLD" \
    '.[] | select(.percentage_used > ($threshold | tonumber)) | 
    "WARNING: \(.session_id) used \(.percentage_used)% of budget"'
```

## Automation

### Cron Job Examples

```cron
# Daily budget report at 9 AM
0 9 * * * python /opt/tokengate/tokengate_cli.py list-sessions > /var/log/tokengate/daily-report.txt

# Check for frozen sessions every hour
0 * * * * python /opt/tokengate/scripts/check-frozen-sessions.sh

# Reset test sessions nightly
0 0 * * * python /opt/tokengate/tokengate_cli.py reset-session test-session --yes
```

## Troubleshooting

### Connection Issues

```bash
# Test Redis connection
python tokengate_cli.py health

# Use custom Redis URL
python tokengate_cli.py --redis-url redis://other-host:6379 health
```

### Session Not Found

```bash
# List all sessions to verify name
python tokengate_cli.py list-sessions

# Sessions are case-sensitive
python tokengate_cli.py get-budget MySession  # Different from my-session
```

## Exit Codes

- `0`: Success
- `1`: Error (check error message)

## Environment Variables

You can set the Redis URL via environment variable:

```bash
export TOKENGATE_REDIS_URL=redis://prod-redis:6379
python tokengate_cli.py --redis-url $TOKENGATE_REDIS_URL list-sessions
```

