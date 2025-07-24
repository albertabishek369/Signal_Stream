from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import Profile, db, Subscription
from forms import LoginForm, SignupForm, PasswordSetupForm
import re
import pytz
from .emails import send_welcome_email

auth_bp = Blueprint('auth', __name__)

def on_new_user_created(user):
    """Sets up a free subscription and sends a welcome email for a new user."""
    existing_sub = Subscription.query.filter_by(user_id=user.id).first()
    if not existing_sub:
        new_sub = Subscription(user_id=user.id, plan_type='free', status='active')
        db.session.add(new_sub)
        db.session.commit()
    
    send_welcome_email(user)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Profile.query.filter_by(email=form.email.data).first()
        if user and user.password_hash and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            if not user.password_hash or not user.timezone:
                flash('Please complete your account setup.', 'info')
                return redirect(url_for('auth.complete_account'))
            flash('Login successful!', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = SignupForm()
    if form.validate_on_submit():
        password = form.password.data
        confirm_password = request.form.get('confirm_password')
        timezone_str = form.timezone.data
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/signup.html', form=form)
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password) or not re.search(r'[\W_]', password):
            flash('Password must contain letters, numbers, and symbols.', 'danger')
            return render_template('auth/signup.html', form=form)
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/signup.html', form=form)
        if timezone_str not in pytz.all_timezones:
            flash('Invalid time zone selected.', 'danger')
            return render_template('auth/signup.html', form=form)

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = Profile(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            timezone=timezone_str,
            phone=form.phone.data
        )
        db.session.add(new_user)
        db.session.commit()
        on_new_user_created(new_user)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/signup.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.home'))

@auth_bp.route('/complete-account', methods=['GET', 'POST'])
@login_required
def complete_account():
    if current_user.password_hash and current_user.timezone:
        return redirect(url_for('main.home'))

    form = PasswordSetupForm()
    if form.validate_on_submit():
        current_user.password_hash = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        current_user.timezone = form.timezone.data
        db.session.commit()
        flash('Your account is now fully set up! You can now log in with your email and password.', 'success')
        return redirect(url_for('main.home'))

    return render_template('auth/complete_account.html', form=form)