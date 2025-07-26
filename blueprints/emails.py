from flask_mail import Message
from extensions import mail
from flask import current_app

def send_email(subject, recipients, body):
    """Helper function to send emails."""
    msg = Message(subject, recipients=recipients, body=body)
    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {recipients}: {e}")

def send_welcome_email(user):
    """Sends a welcome email to a new user."""
    subject = "Welcome to Signal Stream!"
    body = f"Hi {user.username},\n\nWelcome to Signal Stream! We're thrilled to have you on board.\n\nReady to find your first leads? Get started by creating a stream in your dashboard.\n\nThe Signal Stream Team"
    send_email(subject, [user.email], body)

def send_subscription_confirmation_email(user, subscription):
    """Sends an email confirming a new active subscription."""
    subject = "Your Signal Stream Subscription is Active!"
    plan_name = subscription.plan_type.capitalize()
    renewal_date = subscription.current_period_end.strftime('%B %d, %Y')
    body = f"Hi {user.username},\n\nYour subscription to the {plan_name} plan is now active! You're all set to use its features.\n\nYour plan will automatically renew on {renewal_date}.\n\nThank you for subscribing!\n\nThe Signal Stream Team"
    send_email(subject, [user.email], body)

def send_renewal_reminder_email(user, subscription):
    """Sends a subscription renewal reminder."""
    subject = "Your Signal Stream Subscription is Renewing Soon"
    plan_name = subscription.plan_type.capitalize()
    renewal_date = subscription.current_period_end.strftime('%B %d, %Y')
    body = f"Hi {user.username},\n\nThis is a friendly reminder that your subscription to the {plan_name} plan is scheduled to renew in 3 days, on {renewal_date}.\n\nNo action is needed from your end if you wish to continue. If you need to make changes, please visit your settings.\n\nThanks,\nThe Signal Stream Team"
    send_email(subject, [user.email], body)

def send_downgrade_email(user):
    """Informs a user that their plan has expired and they've been moved to the Free plan."""
    subject = "Your Signal Stream Plan Has Expired"
    body = f"Hi {user.username},\n\nYour paid subscription has ended. Your account has been moved to our Free plan.\n\nYou can upgrade again at any time from the pricing page to regain access to premium features.\n\nThanks,\nThe Signal Stream Team"
    send_email(subject, [user.email], body)

def send_subscription_request_email_to_admin(username, email, phone, plan_type, reason):
    """Sends a notification to the admin about a new manual subscription request."""
    subject = f"New Subscription Request: {plan_type.capitalize()} Plan"
    admin_email = current_app.config['ADMIN_EMAIL'] # Add ADMIN_EMAIL to your config
    body = f"""
    A new manual subscription request has been submitted.

    User Details:
    - Username: {username}
    - Email: {email}
    - Phone: {phone or 'Not provided'}
    
    Requested Plan: {plan_type.capitalize()}
    
    Reason for Interest:
    {reason or 'Not provided'}

    Please follow up with the user via email to arrange payment.
    Once payment is confirmed, grant them access via the admin dashboard.
    """
    send_email(subject, [admin_email], body)