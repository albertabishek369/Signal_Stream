import click
from flask import Blueprint

# **FIX:** Do NOT import from the top-level 'app' file here.

commands_bp = Blueprint('commands', __name__, cli_group=None)

@commands_bp.cli.command('check-subscriptions')
def check_subscriptions_command():
    """A CLI command to run the daily subscription check job."""
    # **FIX:** Import the necessary functions locally, inside the command.
    # This breaks the circular import loop.
    from app import create_app
    from .tasks import check_subscriptions
    
    app = create_app()
    check_subscriptions(app)
    print("CLI command: Subscription check finished.")