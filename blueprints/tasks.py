from flask import current_app
from models import db, Subscription, Stream
from datetime import datetime, timedelta, timezone
from .emails import send_downgrade_email, send_renewal_reminder_email

def check_subscriptions(app):
    """
    A daily job to check subscription statuses.
    - Sends renewal reminders for subscriptions ending in 3 days.
    - Downgrades expired subscriptions to the 'free' plan.
    """
    with app.app_context():
        print("Scheduler: Running daily subscription check...")
        now = datetime.now(timezone.utc)
        today = now.date()
        
        # --- Part 1: Send Renewal Reminders ---
        reminder_date = today + timedelta(days=3)
        subscriptions_needing_reminder = Subscription.query.filter(
            Subscription.plan_type != 'free',
            Subscription.status == 'active',
            db.func.date(Subscription.current_period_end) == reminder_date
        ).all()
        
        for sub in subscriptions_needing_reminder:
            print(f"Scheduler: Sending renewal reminder to user {sub.profile.id} for subscription {sub.id}")
            send_renewal_reminder_email(sub.profile, sub)

        # --- Part 2: Downgrade Expired Subscriptions ---
        expired_subscriptions = Subscription.query.filter(
            Subscription.plan_type != 'free',
            Subscription.current_period_end < now
        ).all()

        for sub in expired_subscriptions:
            user = sub.profile
            print(f"Scheduler: Downgrading user {user.id}, subscription {sub.id} has expired.")
            
            streams_to_keep = 1
            user_streams = Stream.query.filter_by(user_id=user.id).order_by(Stream.created_at.asc()).all()
            if len(user_streams) > streams_to_keep:
                for stream_to_delete in user_streams[streams_to_keep:]:
                    db.session.delete(stream_to_delete)

            user.plan = 'free'
            db.session.delete(sub)
            
            free_sub = Subscription(user_id=user.id, plan_type='free', status='active')
            db.session.add(free_sub)
            
            send_downgrade_email(user)
        
        db.session.commit()

        # --- Part 3: Clean Up Unpaid "Created" Subscriptions ---
        one_day_ago = now - timedelta(days=1)
        stale_created_subscriptions = Subscription.query.filter(
            Subscription.status == 'created',
            Subscription.created_at < one_day_ago
        ).all()

        for sub in stale_created_subscriptions:
            print(f"Scheduler: Deleting stale 'created' subscription {sub.id} for user {sub.user_id}.")
            db.session.delete(sub)

        db.session.commit()
        print("Scheduler: Subscription check finished.")