import os
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from flask_apscheduler import APScheduler
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.oauth import oauth_bp, oauth
from blueprints.admin import admin_bp # **NEW:** Import the admin blueprint
# **FIX:** Import the new commands blueprint
from blueprints.commands import commands_bp
# **FIX:** Import the task function from its new location
from blueprints.tasks import check_subscriptions 
from extensions import db, csrf, mail
from config import Config
from flask_migrate import Migrate
from models import Profile, Subscription, PlanLimit, Stream
from datetime import datetime, timedelta, timezone
from blueprints.emails import send_renewal_reminder_email, send_downgrade_email

# Load environment variables from .env file
load_dotenv()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    Migrate(app, db)
    
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'

    # Initialize OAuth
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(admin_bp) # **NEW:** Register the admin blueprint
    # **FIX:** Register the new commands blueprint
    app.register_blueprint(commands_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Profile, user_id)

    # # Initialize and start scheduler
    # scheduler = APScheduler()
    # scheduler.init_app(app)
    
    # # Schedule the job to run once a day
    # if not scheduler.get_job('check_subscriptions_daily'):
    #     scheduler.add_job(
    #         id='check_subscriptions_daily',
    #         func=check_subscriptions,
    #         args=[app],
    #         trigger='interval',
    #         days=1
    #     )
    # scheduler.start()
    
    with app.app_context():
        db.create_all()  # Ensure all tables are created
        # Ensure plan limits are in the database
        if PlanLimit.query.count() == 0:
            limits = [
                PlanLimit(plan_type='free', max_streams=1, daily_analyses=50),
                PlanLimit(plan_type='founder', max_streams=5, daily_analyses=1000),
                PlanLimit(plan_type='scale', max_streams=-1, daily_analyses=10000)  # -1 for unlimited
            ]
            db.session.bulk_save_objects(limits)
            db.session.commit()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
