"""
app/apistack/__init__.py - API Stack 蓝图定义。

API Stack 是一个通用的 API 托管层，提供：
    - 统一的 API 执行入口（/apistack/api/<name>）
    - API 元信息查询（/apistack/info/<name>）
    - Markdown 文档展示（/apistack/api/doc/<name>）
    - 管理员后台（增删改、Token 管理）

导入顺序说明：
    1. 先导入 models  —— 确保 SQLAlchemy 在 create_all() 之前完成表注册
    2. 再导入 handlers —— 将所有处理函数加载进注册表
    3. 最后导入 views  —— 注册路由（views 依赖前两者，必须最后）
"""
from flask import Blueprint

apistack = Blueprint('apistack', __name__, url_prefix='/apistack')

from app.apistack import models   # noqa: F401  E402
from app.apistack import handlers  # noqa: F401  E402
from app.apistack import views     # noqa: F401  E402