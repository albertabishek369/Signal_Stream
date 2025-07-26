from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import Profile, Subscription
from extensions import db
from forms import AdminGrantSubscriptionForm
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator to check if the current user is an admin
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Shows the main admin dashboard."""
    users = Profile.query.order_by(Profile.created_at.desc()).all()
    return render_template('admin/dashboard.html', users=users)


@admin_bp.route('/manage-user/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_user(user_id):
    """Allows an admin to manually grant or update a subscription for a user."""
    user = db.session.get(Profile, user_id)
    if not user:
        abort(404)

    form = AdminGrantSubscriptionForm()
    
    if form.validate_on_submit():
        plan_type = form.plan_type.data
        expiry_date = form.expiry_date.data

        # Find existing subscription or create a new one
        subscription = Subscription.query.filter_by(user_id=user.id).first()
        if not subscription:
            subscription = Subscription(user_id=user.id)
            db.session.add(subscription)

        # Update subscription details
        subscription.plan_type = plan_type
        subscription.status = 'active'
        subscription.current_period_end = datetime.combine(expiry_date, datetime.min.time())
        subscription.razorpay_subscription_id = None # Null for manual subscriptions
        
        # Update the user's main plan field
        user.plan = plan_type
        
        db.session.commit()
        flash(f"Successfully granted '{plan_type}' plan to {user.username} until {expiry_date.strftime('%B %d, %Y')}.", 'success')
        return redirect(url_for('admin.dashboard'))

    # Pre-populate form with existing manual subscription details
    existing_sub = Subscription.query.filter_by(user_id=user.id).first()
    if existing_sub and not existing_sub.razorpay_subscription_id:
        form.plan_type.data = existing_sub.plan_type
        if existing_sub.current_period_end:
            form.expiry_date.data = existing_sub.current_period_end.date()

    return render_template('admin/manage_user.html', user=user, form=form)