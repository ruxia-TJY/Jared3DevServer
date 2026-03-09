"""
app/__init__.py - Flask 应用工厂。

负责创建 Flask 实例、加载配置、初始化扩展，并注册所有蓝图。
调用方式：
    from app import create_app
    app = create_app()
"""
import os
from flask import Flask
from app.extensions import db, login_manager
import config


def create_app() -> Flask:
    """创建并配置 Flask 应用实例（应用工厂模式）。

    执行步骤：
        1. 从 config 模块读取配置项；
        2. 初始化 SQLAlchemy 和 Flask-Login；
        3. 注册 user_loader 回调；
        4. 在应用上下文中建表并注册三个蓝图。

    Returns:
        配置完毕、可直接运行的 Flask 实例。
    """
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
        """Flask-Login 用户加载回调，通过 ID 从数据库查询用户。

        Args:
            user_id: 会话中存储的用户 ID 字符串。

        Returns:
            对应的 User 实例，若不存在则返回 None。
        """
        return db.session.get(User, int(user_id))

    with flask_app.app_context():
        # 确保所有 Model 在 create_all() 前已导入，表结构才能被正确创建
        from app.user.models import User  # noqa: F401
        from app.updatehub.models import AppVersion, AppConfig, AppAccess  # noqa: F401
        from app.apistack.models import ApiEntry, ApiToken  # noqa: F401
        db.create_all()

        from app.updatehub import updatehub
        flask_app.register_blueprint(updatehub)

        from app.auth import auth
        flask_app.register_blueprint(auth)

        from app.user import user
        flask_app.register_blueprint(user)

        from app.apistack import apistack
        flask_app.register_blueprint(apistack)

    return flask_app