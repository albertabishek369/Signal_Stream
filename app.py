import os
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from flask_apscheduler import APScheduler
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.oauth import oauth_bp, oauth
from extensions import db, csrf, mail
from config import Config
from flask_migrate import Migrate
from models import Profile, Subscription, PlanLimit
from datetime import datetime, timedelta, timezone
from blueprints.emails import send_renewal_reminder_email, send_downgrade_email

# Load environment variables from .env file
load_dotenv()

def check_subscriptions(app):
    """
    A daily job to check subscription statuses.
    - Sends renewal reminders for subscriptions ending in 3 days.
    - Downgrades expired subscriptions to the 'free' plan.
    """
    with app.app_context():
        print("Scheduler: Running daily subscription check...")
        
        # 1. Send Renewal Reminders
        reminder_date = datetime.now(timezone.utc).date() + timedelta(days=3)
        subscriptions_needing_reminder = Subscription.query.filter(
            Subscription.plan_type != 'free',
            db.func.date(Subscription.current_period_end) == reminder_date
        ).all()
        
        for sub in subscriptions_needing_reminder:
            print(f"Scheduler: Sending renewal reminder to user {sub.profile.id} for subscription {sub.id}")
            send_renewal_reminder_email(sub.profile, sub)

        # 2. Downgrade Expired Subscriptions
        today = datetime.now(timezone.utc).date()
        expired_subscriptions = Subscription.query.filter(
            Subscription.plan_type != 'free',
            db.func.date(Subscription.current_period_end) < today
        ).all()

        for sub in expired_subscriptions:
            user = sub.profile
            print(f"Scheduler: Downgrading user {user.id}, subscription {sub.id} has expired.")
            
            # Delete the expired subscription
            db.session.delete(sub)
            
            # Create a new free subscription for the user
            free_sub = Subscription(user_id=user.id, plan_type='free', status='active')
            db.session.add(free_sub)
            send_downgrade_email(user)
        
        db.session.commit()
        print("Scheduler: Subscription check finished.")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

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

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Profile, user_id)

    # Initialize and start scheduler
    scheduler = APScheduler()
    scheduler.init_app(app)
    
    # Schedule the job to run once a day
    if not scheduler.get_job('check_subscriptions_daily'):
        scheduler.add_job(
            id='check_subscriptions_daily',
            func=check_subscriptions,
            args=[app],
            trigger='interval',
            days=1
        )
    scheduler.start()
    
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


if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
