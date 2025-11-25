#!/usr/bin/env python3
"""TokenGate CLI - Command-line management tool for budget and session operations."""
import click
import redis
from tabulate import tabulate
from datetime import datetime
import json
from typing import Optional


class TokenGateCLI:
    """CLI for managing TokenGate budgets and sessions."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize CLI with Redis connection."""
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def set_budget(self, session_id: str, amount: float) -> bool:
        """Set budget for a session."""
        try:
            self.redis.set(f"session:{session_id}:budget", str(amount))
            return True
        except Exception as e:
            click.echo(f"Error setting budget: {e}", err=True)
            return False
    
    def get_budget_info(self, session_id: str) -> dict:
        """Get budget information for a session."""
        budget = self.redis.get(f"session:{session_id}:budget")
        spent = self.redis.get(f"session:{session_id}:spent") or "0.0"
        
        if budget:
            budget_val = float(budget)
            spent_val = float(spent)
            remaining = budget_val - spent_val
            
            return {
                "session_id": session_id,
                "budget": budget_val,
                "spent": spent_val,
                "remaining": max(0.0, remaining),
                "percentage_used": (spent_val / budget_val * 100) if budget_val > 0 else 0
            }
        return None
    
    def list_sessions(self) -> list:
        """List all active sessions."""
        sessions = []
        keys = self.redis.keys("session:*:budget")
        
        for key in keys:
            session_id = key.split(":")[1]
            info = self.get_budget_info(session_id)
            if info:
                sessions.append(info)
        
        return sessions
    
    def reset_session(self, session_id: str) -> bool:
        """Reset budget and spending for a session."""
        try:
            self.redis.delete(f"session:{session_id}:budget")
            self.redis.delete(f"session:{session_id}:spent")
            return True
        except Exception as e:
            click.echo(f"Error resetting session: {e}", err=True)
            return False
    
    def freeze_session(self, session_id: str, reason: str = "Manual freeze") -> bool:
        """Freeze a session temporarily."""
        try:
            frozen_until = (datetime.utcnow().timestamp() + 3600)  # 1 hour
            self.redis.setex(
                f"anomaly:{session_id}:frozen_until",
                3600,
                datetime.utcnow().isoformat()
            )
            self.redis.setex(
                f"anomaly:{session_id}:freeze_reason",
                3600,
                reason
            )
            return True
        except Exception as e:
            click.echo(f"Error freezing session: {e}", err=True)
            return False
    
    def unfreeze_session(self, session_id: str) -> bool:
        """Unfreeze a session."""
        try:
            self.redis.delete(f"anomaly:{session_id}:frozen_until")
            self.redis.delete(f"anomaly:{session_id}:freeze_reason")
            return True
        except Exception as e:
            click.echo(f"Error unfreezing session: {e}", err=True)
            return False
    
    def get_anomaly_stats(self, session_id: str) -> dict:
        """Get anomaly detection stats for a session."""
        frozen_until = self.redis.get(f"anomaly:{session_id}:frozen_until")
        freeze_reason = self.redis.get(f"anomaly:{session_id}:freeze_reason")
        request_count = self.redis.get(f"anomaly:{session_id}:requests:1min") or 0
        
        return {
            "session_id": session_id,
            "is_frozen": frozen_until is not None,
            "freeze_reason": freeze_reason,
            "requests_last_minute": int(request_count)
        }


@click.group()
@click.option('--redis-url', default='redis://localhost:6379', help='Redis connection URL')
@click.pass_context
def cli(ctx, redis_url):
    """TokenGate CLI - Manage budgets and sessions."""
    ctx.obj = TokenGateCLI(redis_url)


@cli.command()
@click.argument('session_id')
@click.argument('amount', type=float)
@click.pass_obj
def set_budget(cli_obj, session_id, amount):
    """Set budget for a session.
    
    Example: tokengate set-budget my-session 25.50
    """
    if cli_obj.set_budget(session_id, amount):
        click.echo(f"✓ Budget set for '{session_id}': ${amount:.2f}")
    else:
        click.echo("✗ Failed to set budget", err=True)


@cli.command()
@click.argument('session_id')
@click.pass_obj
def get_budget(cli_obj, session_id):
    """Get budget information for a session.
    
    Example: tokengate get-budget my-session
    """
    info = cli_obj.get_budget_info(session_id)
    if info:
        click.echo(f"\nSession: {info['session_id']}")
        click.echo(f"Budget:    ${info['budget']:.4f}")
        click.echo(f"Spent:     ${info['spent']:.4f}")
        click.echo(f"Remaining: ${info['remaining']:.4f}")
        click.echo(f"Used:      {info['percentage_used']:.1f}%\n")
    else:
        click.echo(f"✗ Session '{session_id}' not found", err=True)


@cli.command()
@click.option('--format', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_obj
def list_sessions(cli_obj, format):
    """List all active sessions.
    
    Example: tokengate list-sessions
    """
    sessions = cli_obj.list_sessions()
    
    if not sessions:
        click.echo("No active sessions found.")
        return
    
    if format == 'json':
        click.echo(json.dumps(sessions, indent=2))
    else:
        headers = ["Session ID", "Budget", "Spent", "Remaining", "Used %"]
        rows = [
            [
                s['session_id'],
                f"${s['budget']:.4f}",
                f"${s['spent']:.4f}",
                f"${s['remaining']:.4f}",
                f"{s['percentage_used']:.1f}%"
            ]
            for s in sessions
        ]
        click.echo("\n" + tabulate(rows, headers=headers, tablefmt="grid") + "\n")


@cli.command()
@click.argument('session_id')
@click.confirmation_option(prompt='Are you sure you want to reset this session?')
@click.pass_obj
def reset_session(cli_obj, session_id):
    """Reset budget and spending for a session.
    
    Example: tokengate reset-session my-session
    """
    if cli_obj.reset_session(session_id):
        click.echo(f"✓ Session '{session_id}' reset successfully")
    else:
        click.echo("✗ Failed to reset session", err=True)


@cli.command()
@click.argument('session_id')
@click.option('--reason', default='Manual freeze', help='Reason for freezing')
@click.pass_obj
def freeze_session(cli_obj, session_id, reason):
    """Freeze a session temporarily.
    
    Example: tokengate freeze-session my-session --reason "Suspicious activity"
    """
    if cli_obj.freeze_session(session_id, reason):
        click.echo(f"✓ Session '{session_id}' frozen")
    else:
        click.echo("✗ Failed to freeze session", err=True)


@cli.command()
@click.argument('session_id')
@click.pass_obj
def unfreeze_session(cli_obj, session_id):
    """Unfreeze a session.
    
    Example: tokengate unfreeze-session my-session
    """
    if cli_obj.unfreeze_session(session_id):
        click.echo(f"✓ Session '{session_id}' unfrozen")
    else:
        click.echo("✗ Failed to unfreeze session", err=True)


@cli.command()
@click.argument('session_id')
@click.pass_obj
def anomaly_stats(cli_obj, session_id):
    """Get anomaly detection statistics for a session.
    
    Example: tokengate anomaly-stats my-session
    """
    stats = cli_obj.get_anomaly_stats(session_id)
    
    click.echo(f"\nAnomaly Stats for: {stats['session_id']}")
    click.echo(f"Frozen: {'Yes' if stats['is_frozen'] else 'No'}")
    if stats['is_frozen']:
        click.echo(f"Reason: {stats['freeze_reason']}")
    click.echo(f"Requests (last minute): {stats['requests_last_minute']}\n")


@cli.command()
@click.pass_obj
def health(cli_obj):
    """Check Redis connection health.
    
    Example: tokengate health
    """
    try:
        cli_obj.redis.ping()
        click.echo("✓ Redis connection healthy")
    except Exception as e:
        click.echo(f"✗ Redis connection failed: {e}", err=True)


if __name__ == '__main__':
    cli()

