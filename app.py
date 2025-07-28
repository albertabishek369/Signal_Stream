import os
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.oauth import oauth_bp, oauth
from blueprints.admin import admin_bp
from blueprints.commands import commands_bp 
from blueprints.tasks import check_subscriptions
from extensions import db, csrf, mail
from config import Config
from flask_migrate import Migrate
from models import Profile, PlanLimit

load_dotenv()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    Migrate(app, db)
    
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'

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
    app.register_blueprint(admin_bp)
    app.register_blueprint(commands_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Profile, user_id)

    with app.app_context():
        if PlanLimit.query.count() == 0:
            limits = [
                PlanLimit(plan_type='free', max_streams=1, daily_analyses=50),
                PlanLimit(plan_type='founder', max_streams=5, daily_analyses=1000),
                PlanLimit(plan_type='scale', max_streams=-1, daily_analyses=10000)
            ]
            db.session.bulk_save_objects(limits)
            db.session.commit()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)