"""
app/extensions.py - 共享 Flask 扩展实例。

将扩展对象单独定义，避免循环导入：
    - db           : SQLAlchemy ORM 实例
    - login_manager: Flask-Login 会话管理实例
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录后再访问该页面'
login_manager.login_message_category = 'warning'