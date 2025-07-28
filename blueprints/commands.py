import click
from flask import Blueprint
from app import create_app
# **FIX:** Import the task from its new, non-circular location
from .tasks import check_subscriptions

commands_bp = Blueprint('commands', __name__, cli_group=None)

@commands_bp.cli.command('check-subscriptions')
def check_subscriptions_command():
    """A CLI command to run the daily subscription check job."""
    app = create_app()
    check_subscriptions(app)
    print("CLI command: Subscription check finished.")