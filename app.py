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
from extensions import db, csrf, mail
from config import Config
from flask_migrate import Migrate
from models import Profile, Subscription, PlanLimit, Stream
from datetime import datetime, timedelta, timezone
from blueprints.emails import send_renewal_reminder_email, send_downgrade_email

# Load environment variables from .env file
load_dotenv()

def check_subscriptions(app):
    """
    A daily job to check all subscription statuses and handle expirations.
    """
    with app.app_context():
        print("Scheduler: Running daily subscription check...")
        now = datetime.now(timezone.utc)
        today = now.date()
        one_day_ago = now - timedelta(days=1)

        # --- Part 1: Handle Expired Paid Subscriptions (Both Manual and Razorpay) ---
        # This finds any plan whose end date is in the past.
        expired_subscriptions = Subscription.query.filter(
            Subscription.plan_type != 'free',
            Subscription.current_period_end < now
        ).all()

        for sub in expired_subscriptions:
            user = sub.profile
            print(f"Scheduler: Downgrading user {user.id}, subscription {sub.id} has expired.")
            
            # Delete extra streams, keeping the oldest one
            streams_to_keep = 1
            user_streams = Stream.query.filter_by(user_id=user.id).order_by(Stream.created_at.asc()).all()
            if len(user_streams) > streams_to_keep:
                for stream_to_delete in user_streams[streams_to_keep:]:
                    db.session.delete(stream_to_delete)

            # Update user's plan back to free
            user.plan = 'free'
            # Delete the expired subscription record
            db.session.delete(sub)
            
            # Create a new 'free' subscription record
            free_sub = Subscription(user_id=user.id, plan_type='free', status='active')
            db.session.add(free_sub)
            
            send_downgrade_email(user)
        
        db.session.commit() # Commit after the first batch of changes

        # --- Part 2: Clean Up Unpaid "Created" Subscriptions ---
        # This finds any Razorpay subscription that was created more than a day ago
        # but was never paid and activated.
        stale_created_subscriptions = Subscription.query.filter(
            Subscription.status == 'created',
            Subscription.created_at < one_day_ago
        ).all()

        for sub in stale_created_subscriptions:
            user = sub.profile
            print(f"Scheduler: Deleting stale 'created' subscription {sub.id} for user {user.id}.")
            # The user's plan on the Profile model was never upgraded, so we just delete
            # the abandoned subscription record.
            db.session.delete(sub)

        db.session.commit() # Commit after the second batch of changes

        print("Scheduler: Subscription check finished.")
        
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

app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
