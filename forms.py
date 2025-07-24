from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, RadioField
# **FIX:** Import the 'Optional' validator
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional



class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign in')

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    phone = StringField('Phone Number', validators=[DataRequired()])
    timezone = SelectField('Time Zone', choices=[
        ('UTC', 'UTC'),
        ('Asia/Kolkata', 'IST (India)'),
        ('America/New_York', 'EST (New York)'),
        ('Europe/London', 'GMT (London)')
    ], default='UTC', validators=[DataRequired()])
    submit = SubmitField('Create Account')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ProductForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    product_description = TextAreaField('Product Description', validators=[DataRequired()])
    target_audience = StringField('Target Audience', validators=[DataRequired()])
    pain_points_solved = TextAreaField('Pain Points Solved', validators=[DataRequired()])
    submit = SubmitField('Save Product')

REDDIT_COMMUNITY_CHOICES = [
    ('r/SaaS', 'r/SaaS'),
    ('r/Entrepreneur', 'r/Entrepreneur'),
    ('r/sideproject', 'r/sideproject'),
    ('r/startups', 'r/startups'),
    ('r/indiehackers', 'r/indiehackers')
]

class StreamForm(FlaskForm):
    product_id = SelectField('Product', coerce=str, validators=[DataRequired()])
    stream_name = StringField('Stream Name', validators=[DataRequired(), Length(min=3)])
    platform = RadioField('Platform', choices=[('reddit', 'Reddit'), ('youtube', 'YouTube'), ('product_hunt', 'Product Hunt')], validators=[DataRequired()])
    
    target = StringField('Keyword or YouTube Video ID')
    
    # **FIX:** Add the 'Optional()' validator to this field.
    # This tells WTForms that it's okay if this field isn't included in the form submission.
    reddit_target = SelectField('Community', validators=[Optional()])

    ai_strictness = RadioField('AI Strictness', choices=[('strict', 'Very Strict'), ('medium', 'Medium'), ('liberal', 'Liberal')], default='medium', validators=[DataRequired()])
    execution_frequency_minutes = SelectField('Check Frequency', choices=[(15, 'Every 15 minutes'), (60, 'Hourly'), (360, 'Every 6 hours'), (1440, 'Daily')], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Stream')

class PasswordSetupForm(FlaskForm):
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    timezone = SelectField('Time Zone', choices=[
        ('UTC', 'UTC'),
        ('Asia/Kolkata', 'IST (India)'),
        ('America/New_York', 'EST (New York)'),
        ('Europe/London', 'GMT (London)')
    ], default='UTC', validators=[DataRequired()])
    submit = SubmitField('Set Password')


# **NEW:** Form for updating user profile information
class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    phone = StringField('Phone Number', validators=[Optional(), Length(min=10, max=20)])
    timezone = SelectField('Time Zone', choices=[
        ('UTC', 'UTC'),
        ('Asia/Kolkata', 'IST (India)'),
        ('America/New_York', 'EST (New York)'),
        ('Europe/London', 'GMT (London)')
    ], validators=[DataRequired()])
    submit = SubmitField('Save Changes')