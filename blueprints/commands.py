# blueprints/commands.py

import click
from flask import Blueprint
from app import check_subscriptions, create_app

commands_bp = Blueprint('commands', __name__, cli_group=None)

@commands_bp.cli.command('check-subscriptions')
def check_subscriptions_command():
    """A CLI command to run the daily subscription check job."""
    # We create a temporary app instance to have the right context
    app = create_app()
    check_subscriptions(app)
    print("CLI command: Subscription check finished.")