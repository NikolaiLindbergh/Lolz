from flask import Flask
from flask_login import LoginManager
from config import Config
from database.models import db, User
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Custom Jinja2 filter
    import json as _json
    @app.template_filter('from_json')
    def from_json(value):
        try:
            return _json.loads(value)
        except Exception:
            return {}

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    # Create tables and default admin on first run
    with app.app_context():
        db.create_all()
        _seed_admin()

    return app

def _seed_admin():
    """Create default admin account if none exists."""
    from database.models import User
    if not User.query.filter_by(role='admin').first():
        admin = User(
            username='admin',
            email='admin@healthcare.local',
            full_name='System Administrator',
            role='admin',
            is_active=True
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
        print("Default admin created - username: admin | password: Admin@1234")

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host=Config.HOST, port=Config.PORT)
