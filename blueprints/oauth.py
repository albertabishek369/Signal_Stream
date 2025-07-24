from flask import Blueprint, url_for, redirect, flash
from flask_login import login_user
from authlib.integrations.flask_client import OAuth
from models import db, Profile, Subscription
import secrets
from .emails import send_welcome_email

oauth_bp = Blueprint('oauth', __name__)
oauth = OAuth()

def on_new_user_created(user):
    """Sets up a free subscription and sends a welcome email for a new user."""
    existing_sub = Subscription.query.filter_by(user_id=user.id).first()
    if not existing_sub:
        new_sub = Subscription(user_id=user.id, plan_type='free', status='active')
        db.session.add(new_sub)
        db.session.commit()
    
    send_welcome_email(user)

def handle_google_login(user_info):
    google_id = user_info.get('sub')
    email = user_info.get('email')
    
    if not google_id or not email:
        flash('Google login failed. Could not retrieve required information.', 'danger')
        return redirect(url_for('auth.login'))

    user = Profile.query.filter_by(google_id=google_id).first()
    if user:
        login_user(user)
        if not user.password_hash or not user.timezone:
            flash('Please complete your account setup.', 'info')
            return redirect(url_for('auth.complete_account'))
        return redirect(url_for('main.home'))

    user = Profile.query.filter_by(email=email).first()
    if user:
        user.google_id = google_id
        db.session.commit()
        login_user(user)
        if not user.password_hash or not user.timezone:
            flash('Please complete your account setup.', 'info')
            return redirect(url_for('auth.complete_account'))
        flash('Your Google account has been linked to your existing account.', 'success')
        return redirect(url_for('main.home'))

    new_user = Profile(
        username=f"{user_info.get('given_name', 'user')}_{secrets.token_hex(4)}",
        email=email,
        password_hash=None,
        timezone=None,
        google_id=google_id
    )
    db.session.add(new_user)
    db.session.commit()
    on_new_user_created(new_user)
    login_user(new_user)
    flash('Welcome to Signal Stream! Please complete your account setup.', 'info')
    return redirect(url_for('auth.complete_account'))

@oauth_bp.route('/login/google')
def login_google():
    redirect_uri = url_for('oauth.authorize_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@oauth_bp.route('/login/google/callback')
def authorize_google():
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
        return handle_google_login(user_info)
    except Exception as e:
        flash(f'An error occurred during Google login: {e}', 'danger')
        return redirect(url_for('auth.login'))