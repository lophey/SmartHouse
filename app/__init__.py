from flask import Flask, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')  # Шляхи до шаблонів та статики
    app.config.from_object('config.Config')

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = 'user.login'

    # Додатковий обробник для адміністраторів
    @login_manager.unauthorized_handler
    def unauthorized():
        # Якщо запит був до адмінської зони - перенаправляємо на адмінський вхід
        if request.path.startswith('/admin'):
            return redirect(url_for('admin.login'))
        return redirect(url_for('user.login'))

    with app.app_context():
        # Реєстрація блюпрінтів
        from app.controllers.admin_routes import admin_bp
        from app.controllers.user_routes import user_bp
        from app.controllers.base import base_bp

        from app.controllers.device_controller import admin_device_bp, user_device_bp

        # Регистрируем Blueprint для админской части
        app.register_blueprint(admin_device_bp)

        # Регистрируем Blueprint для пользовательской части
        app.register_blueprint(user_device_bp)

        app.register_blueprint(admin_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(base_bp)

        # Створення таблиць БД
        db.create_all()

    return app



