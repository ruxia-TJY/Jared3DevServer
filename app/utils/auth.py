from functools import wraps
from flask import request, jsonify, redirect, url_for, abort
from flask_login import current_user
import config


def require_token(f):
    """验证请求中的上传 Token，支持 Header / Form / JSON 三种方式传入。"""
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
    """仅管理员可访问，未登录跳转登录页，非管理员返回 403。"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated