"""
app/utils/auth.py - 认证与授权装饰器。

提供：
    require_token   - API 端点 Token 校验装饰器（管理类接口）
    admin_required  - 仅管理员可访问的页面路由装饰器
"""
from functools import wraps
from flask import request, jsonify, redirect, url_for, abort
from flask_login import current_user
import config


def require_token(f):
    """校验上传 Token 的装饰器（用于管理类 API 端点）。

    Token 可通过以下任意方式传入：
        - HTTP Header ``X-Upload-Token``
        - Form 字段 ``token``
        - JSON body 字段 ``token``

    Args:
        f: 被装饰的视图函数。

    Returns:
        包装后的视图函数。Token 正确时执行原函数；
        Token 缺失或错误时返回 ``{"error": "无效的 Token"}``（HTTP 401）。
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = (
            request.headers.get('X-Upload-Token')
            or request.form.get('token')
            or (request.get_json(silent=True) or {}).get('token')
        )
        if token != config.UPLOAD_TOKEN:
            return jsonify({'error': '无效的 Token'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """仅管理员可访问的页面路由装饰器。

    检查顺序：
        1. 未登录 → 重定向到登录页（携带 ``next`` 参数）；
        2. 已登录但非管理员 → 中止并返回 403；
        3. 已登录且为管理员 → 正常执行视图函数。

    Args:
        f: 被装饰的视图函数。

    Returns:
        包装后的视图函数。
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated