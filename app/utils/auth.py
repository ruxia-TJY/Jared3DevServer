from functools import wraps
from flask import request, jsonify
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
