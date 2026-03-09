import os
from flask import Flask
from app.extensions import db
import config


def create_app() -> Flask:
    """应用工厂函数，创建并配置 Flask 实例。"""
    flask_app = Flask(__name__)
    flask_app.config['MAX_CONTENT_LENGTH']             = config.MAX_CONTENT_LENGTH
    flask_app.config['SQLALCHEMY_DATABASE_URI']        = config.SQLALCHEMY_DATABASE_URI
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    flask_app.config['SQLALCHEMY_ENGINE_OPTIONS']      = config.SQLALCHEMY_ENGINE_OPTIONS

    db.init_app(flask_app)

    with flask_app.app_context():
        db.create_all()

        from app.updatehub import updatehub
        flask_app.register_blueprint(updatehub)

        from app.web import web
        flask_app.register_blueprint(web)

    return flask_app
