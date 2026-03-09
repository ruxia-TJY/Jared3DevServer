import os
from flask import Flask
from app.extensions import db, login_manager
import config


def create_app() -> Flask:
    """应用工厂函数，创建并配置 Flask 实例。"""
    flask_app = Flask(__name__)
    flask_app.config['SECRET_KEY']                     = config.SECRET_KEY
    flask_app.config['MAX_CONTENT_LENGTH']             = config.MAX_CONTENT_LENGTH
    flask_app.config['SQLALCHEMY_DATABASE_URI']        = config.SQLALCHEMY_DATABASE_URI
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS']      = config.SQLALCHEMY_ENGINE_OPTIONS

    db.init_app(flask_app)
    login_manager.init_app(flask_app)

    # user_loader 放在工厂内，避免循环导入
    from app.user.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with flask_app.app_context():
        db.create_all()

        from app.updatehub import updatehub
        flask_app.register_blueprint(updatehub)

        from app.auth import auth
        flask_app.register_blueprint(auth)

        from app.user import user
        flask_app.register_blueprint(user)

    return flask_app