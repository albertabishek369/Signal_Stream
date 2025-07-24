import uuid
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app
# **FIX:** Import the new constant from forms.py
from forms import ProductForm, ProfileForm, StreamForm, REDDIT_COMMUNITY_CHOICES

from models import Product, Stream, Lead, Subscription, PlanLimit, Profile
from extensions import db, razorpay_client, csrf
from flask_login import login_required, current_user
import os
from datetime import datetime, timezone
from blueprints.emails import send_subscription_confirmation_email

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = current_user.id
    streams = Stream.query.filter_by(user_id=user_id).all()
    leads = Lead.query.filter_by(user_id=user_id).order_by(Lead.created_at.desc()).limit(50).all()
    products = Product.query.filter_by(user_id=user_id).all()
    
    # Get unique platforms for the filter dropdown
    platforms = db.session.query(Lead.source_platform).filter_by(user_id=user_id).distinct().all()
    platforms = [p[0] for p in platforms]
    
    return render_template('dashboard.html', streams=streams, leads=leads, products=products, platforms=platforms)

@main_bp.route('/filter-leads')
@login_required
def filter_leads():
    """Endpoint to fetch filtered leads for the dashboard."""
    user_id = current_user.id
    stream_id = request.args.get('stream_id')
    platform = request.args.get('platform')
    status = request.args.get('status')
    
    query = Lead.query.filter_by(user_id=user_id)
    
    if stream_id and stream_id != 'all':
        query = query.filter_by(stream_id=stream_id)
    if platform and platform != 'all':
        query = query.filter_by(source_platform=platform)
    if status and status != 'all':
        query = query.filter_by(status=status)
        
    leads = query.order_by(Lead.created_at.desc()).limit(100).all()
    
    return render_template('includes/lead_feed_partial.html', leads=leads)

@main_bp.route('/update-lead-status/<lead_id>', methods=['POST'])
@login_required
def update_lead_status(lead_id):
    """Endpoint to update the status of a lead."""
    lead = Lead.query.filter_by(lead_id=lead_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['new', 'viewed', 'archived']:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400

    lead.status = new_status
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': f'Lead marked as {new_status}'})

@main_bp.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    form = ProductForm()
    user_id = current_user.id
    if form.validate_on_submit():
        new_product = Product(
            user_id=user_id,
            product_name=form.product_name.data,
            product_description=form.product_description.data,
            target_audience=form.target_audience.data,
            pain_points_solved=form.pain_points_solved.data
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product created successfully!', 'success')
        return redirect(url_for('main.products'))
    products = Product.query.filter_by(user_id=user_id).all()
    streams = Stream.query.filter_by(user_id=user_id).all() # For sidebar
    return render_template('products.html', form=form, products=products, streams=streams)

@main_bp.route('/streams/new', methods=['GET', 'POST'])
@login_required
def new_stream():
    form = StreamForm()
    user_id = current_user.id
    
    # Populate product choices for the dropdown
    products = Product.query.filter_by(user_id=user_id).all()
    form.product_id.choices = [(p.product_id, p.product_name) for p in products]

    # **FIX:** Explicitly set the choices for the Reddit dropdown on every request
    form.reddit_target.choices = REDDIT_COMMUNITY_CHOICES
    
    if not products:
        flash('You need to create a product before you can create a stream.', 'info')
        return redirect(url_for('main.products'))
    
    if request.method == 'POST':
        platform = request.form.get('platform')
        target = request.form.get('target')
        
        if platform in ['youtube', 'product_hunt'] and not target:
            form.target.errors.append('This field is required for the selected platform.')
            
    if form.validate_on_submit():
        # ... (rest of the function logic remains the same) ...
        subscription = Subscription.query.filter_by(user_id=user_id).first()
        limits = PlanLimit.query.filter_by(plan_type=subscription.plan_type).first()
        current_streams_count = Stream.query.filter_by(user_id=user_id).count()

        if limits and limits.max_streams != -1 and current_streams_count >= limits.max_streams:
            flash('You have reached your plan’s stream limit. Please upgrade.', 'danger')
            return redirect(url_for('main.pricing', reason='limit_reached'))

        target_value = form.reddit_target.data if form.platform.data == 'reddit' else form.target.data

        new_stream = Stream(
            user_id=user_id,
            product_id=form.product_id.data,
            stream_name=form.stream_name.data,
            platform=form.platform.data,
            target=target_value,
            ai_strictness=form.ai_strictness.data,
            execution_frequency_minutes=form.execution_frequency_minutes.data,
            is_active=True
        )
        db.session.add(new_stream)
        db.session.commit()
        flash('Stream created successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    streams = Stream.query.filter_by(user_id=user_id).order_by(Stream.created_at.desc()).all()
    return render_template('new_stream.html', form=form, products=products, streams=streams)

@main_bp.route('/pricing')
def pricing():
    reason = request.args.get('reason')
    return render_template('pricing.html', reason=reason)

@main_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    user_id = current_user.id
    
    # **MODIFIED:** Create an instance of the ProfileForm and pre-populate it
    profile_form = ProfileForm(obj=current_user)
    
    subscription = Subscription.query.filter_by(user_id=user_id).order_by(Subscription.created_at.desc()).first()
    if not subscription:
        subscription = Subscription(user_id=user_id, plan_type='free', status='active')
        db.session.add(subscription)
        db.session.commit()
    
    products = Product.query.filter_by(user_id=user_id).all()
    streams = Stream.query.filter_by(user_id=user_id).all()
    
    # **MODIFIED:** Pass the profile_form to the template
    return render_template('settings.html', subscription=subscription, products=products, streams=streams, profile_form=profile_form)


# **NEW:** Add this route to handle profile updates
@main_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        # Update user's profile with the new data
        current_user.username = form.username.data
        current_user.phone = form.phone.data
        current_user.timezone = form.timezone.data
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
    else:
        # If validation fails, flash the errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')
                
    return redirect(url_for('main.settings'))

@main_bp.route('/create-subscription', methods=['POST'])
@login_required
def create_subscription():
    user_id = current_user.id
    plan_type = request.get_json().get('plan_type')
    plan_ids = {'founder': 'plan_QwswYisjnDCDY6', 'scale': 'plan_Qwt1O8dXzFcNNF'}
    
    if plan_type not in plan_ids:
        return jsonify({'error': 'Invalid plan type'}), 400

    current_sub = Subscription.query.filter_by(user_id=user_id).first()
    if current_sub and current_sub.status == 'active' and current_sub.plan_type != 'free':
        flash('You already have an active subscription. Please manage it from your settings.', 'info')
        return jsonify({'error': 'Active subscription already exists'}), 400

    try:
        subscription_payload = {
            'plan_id': plan_ids[plan_type],
            'customer_notify': 1,
            'total_count': 12,
            'notes': {'user_id': str(user_id)}
        }
        rzp_subscription = razorpay_client.subscription.create(subscription_payload)
        
        if current_sub and current_sub.plan_type == 'free':
            db.session.delete(current_sub)
            db.session.commit()

        new_sub = Subscription(
            user_id=user_id,
            plan_type=plan_type,
            status='created', # Set status to 'created' initially
            razorpay_subscription_id=rzp_subscription['id']
        )
        db.session.add(new_sub)
        db.session.commit()
        
        return jsonify({
            'subscription_id': rzp_subscription['id'],
            'key_id': os.getenv('RAZORPAY_KEY_ID'),
            'user_email': current_user.email,
            'user_name': current_user.username
        })
    except Exception as e:
        current_app.logger.error(f"Razorpay subscription creation failed for user {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/webhooks/razorpay', methods=['POST'])
@csrf.exempt
def razorpay_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Razorpay-Signature')
    
    try:
        razorpay_client.utility.verify_webhook_signature(
            payload.decode('utf-8'), signature, os.getenv('RAZORPAY_WEBHOOK_SECRET')
        )
    except Exception as e:
        current_app.logger.error(f"Razorpay webhook signature verification failed: {e}")
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
    
    event = request.get_json()
    event_type = event.get('event')
    
    if event_type == 'subscription.activated' or event_type == 'subscription.charged':
        subscription_data = event['payload']['subscription']['entity']
        razorpay_sub_id = subscription_data['id']
        
        sub_to_update = Subscription.query.filter_by(razorpay_subscription_id=razorpay_sub_id).first()

        if not sub_to_update:
            current_app.logger.error(f"Webhook received for unknown subscription ID: {razorpay_sub_id}")
            return jsonify({'status': 'error', 'message': 'Subscription not found in our database'}), 404
        
        user = sub_to_update.profile
        
        sub_to_update.status = 'active'
        sub_to_update.current_period_end = datetime.fromtimestamp(subscription_data['current_end'], tz=timezone.utc)
        db.session.commit()

        if event_type == 'subscription.activated':
            send_subscription_confirmation_email(user, sub_to_update)

        current_app.logger.info(f"Subscription {sub_to_update.id} for user {user.id} was updated to '{sub_to_update.status}'")

    return jsonify({'status': 'success'})


@main_bp.route('/terms') 
@login_required
def terms_of_service():
    """Renders the Terms of Service page."""
    # These queries are necessary to correctly render the sidebar
    user_id = current_user.id
    streams = Stream.query.filter_by(user_id=user_id).all()
    products = Product.query.filter_by(user_id=user_id).all()
    return render_template('terms.html', streams=streams, products=products)

@main_bp.route('/privacy')
@login_required
def privacy_policy():
    """Renders the Privacy Policy page."""
    # These queries are necessary to correctly render the sidebar
    user_id = current_user.id
    streams = Stream.query.filter_by(user_id=user_id).all()
    products = Product.query.filter_by(user_id=user_id).all()
    return render_template('privacy.html', streams=streams, products=products)

@main_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancels the user's active Razorpay subscription."""
    user_id = current_user.id
    sub = Subscription.query.filter_by(user_id=user_id, status='active').first()

    if not sub or not sub.razorpay_subscription_id:
        flash('No active subscription found to cancel.', 'danger')
        return redirect(url_for('main.settings'))

    try:
        # Tell Razorpay to cancel the subscription at the end of the current billing cycle
        razorpay_client.subscription.cancel(sub.razorpay_subscription_id)
        
        # Update our local database status
        sub.status = 'canceled'
        db.session.commit()
        
        flash('Your subscription has been canceled. You will retain access until the end of the current billing period.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error canceling subscription for user {user_id}: {e}")
        flash('There was an error canceling your subscription. Please contact support.', 'danger')
        
    return redirect(url_for('main.settings'))


@main_bp.route('/reactivate-subscription', methods=['POST'])
@login_required
def reactivate_subscription():
    """Reactivates a user's canceled Razorpay subscription."""
    user_id = current_user.id
    sub = Subscription.query.filter_by(user_id=user_id, status='canceled').first()

    if not sub:
        flash('No canceled subscription found to reactivate.', 'danger')
        return redirect(url_for('main.settings'))
    
    # NOTE: Razorpay does not have a direct "reactivate" API.
    # The standard flow is to guide the user to subscribe again.
    # This provides a clear path for the user.
    flash('To reactivate your plan, please choose it again from the pricing page.', 'info')
    return redirect(url_for('main.pricing'))