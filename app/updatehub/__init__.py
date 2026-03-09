from flask import Blueprint

updatehub = Blueprint('updatehub', __name__, url_prefix='/updatehub')

# 注册各路由模块（import 触发路由装饰器注册）
from app.updatehub import apps, versions, download, manage  # noqa: E402, F401
