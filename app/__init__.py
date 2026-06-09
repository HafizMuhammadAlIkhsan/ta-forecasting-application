from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.cli import init_db, seed, db_reset
from flask_mail import Mail

mail = Mail()
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    from config import Config
    app.config.from_object(Config)

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Silakan login terlebih dahulu."
    login_manager.login_message_category = "warning"

    from app.controllers.auth_controller import auth_bp
    from app.controllers.main_controller import main_bp
    # from app.controllers.dashboard_controller import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    # app.register_blueprint(dashboard_bp)
    
    app.cli.add_command(init_db)
    app.cli.add_command(seed)
    app.cli.add_command(db_reset)
    
    return app
