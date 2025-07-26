from extensions import db
from uuid import uuid4
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

class Profile(db.Model, UserMixin):
    __tablename__ = 'profiles'
    id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid4()))
    username = db.Column(db.Text, unique=True, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=True)
    timezone = db.Column(db.Text, default='UTC')
    phone = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    google_id = db.Column(db.Text, unique=True, nullable=True)
    plan = db.Column(db.Text, nullable=False, default='free')

        # **NEW:** Add this field to identify admin users
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # **NEW:** Add this field to store the Razorpay customer ID
    razorpay_customer_id = db.Column(db.Text, unique=True, nullable=True)
    # Relationships
    subscription = db.relationship('Subscription', backref='profile', uselist=False, cascade="all, delete-orphan")
    products = db.relationship('Product', backref='profile', lazy='dynamic', cascade="all, delete-orphan")
    streams = db.relationship('Stream', backref='profile', lazy='dynamic', cascade="all, delete-orphan")
    leads = db.relationship('Lead', backref='profile', lazy='dynamic', cascade="all, delete-orphan")
    analysis_logs = db.relationship('AnalysisLog', backref='profile', lazy='dynamic', cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=max_age)['user_id']
        except:
            return None
        return Profile.query.get(user_id)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Text, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    plan_type = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False)
    razorpay_subscription_id = db.Column(db.Text, unique=True, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Text, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    product_name = db.Column(db.Text, nullable=False)
    product_description = db.Column(db.Text, nullable=False)
    target_audience = db.Column(db.Text, nullable=True)
    pain_points_solved = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Stream(db.Model):
    __tablename__ = 'streams'
    stream_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Text, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Text, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
    stream_name = db.Column(db.Text, nullable=False)
    platform = db.Column(db.Text, nullable=False)
    target = db.Column(db.Text, nullable=False)
    ai_strictness = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    execution_frequency_minutes = db.Column(db.Integer, nullable=False)
    last_executed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.Text, default='active')
    status_message = db.Column(db.Text, nullable=True)

class Lead(db.Model):
    __tablename__ = 'leads'
    lead_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Text, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    stream_id = db.Column(db.Text, db.ForeignKey('streams.stream_id', ondelete='CASCADE'), nullable=False)
    source_platform = db.Column(db.Text, nullable=False)
    author_username = db.Column(db.Text, nullable=True)
    content_text = db.Column(db.Text, nullable=False)
    content_url = db.Column(db.Text, nullable=True)
    ai_reasoning = db.Column(db.Text, nullable=True)
    ai_pain_point = db.Column(db.Text, nullable=True)
    status = db.Column(db.Text, default='new')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('user_id', 'content_url', name='unique_lead_url_for_user'),)

class PlanLimit(db.Model):
    __tablename__ = 'plan_limits'
    plan_type = db.Column(db.Text, primary_key=True)
    max_streams = db.Column(db.Integer, nullable=False)
    daily_analyses = db.Column(db.Integer, nullable=False)

class AnalysisLog(db.Model):
    __tablename__ = 'analysis_logs'
    log_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Text, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class JobQueue(db.Model):
    __tablename__ = 'job_queue'
    job_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid4()))
    stream_id = db.Column(db.Text, db.ForeignKey('streams.stream_id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Text, nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = db.Column(db.DateTime, nullable=True)