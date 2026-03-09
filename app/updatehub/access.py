"""
updatehub 访问控制辅助模块。

访问级别：
  public     - 无需登录，任何人可访问
  protected  - 需要登录（任何已认证用户）
  restricted - 仅指定用户 + 管理员
"""
from flask import jsonify, redirect, url_for, request, render_template
from flask_login import current_user

from app.extensions import db
from app.updatehub.models import AppConfig, AppAccess, ACCESS_PUBLIC, ACCESS_PROTECTED


def get_access_level(app_name: str) -> str:
    """获取软件的访问级别。

    查询 AppConfig 表，若无记录则默认返回 ``ACCESS_PUBLIC``。

    Args:
        app_name: 软件名称。

    Returns:
        访问级别字符串：``'public'`` / ``'protected'`` / ``'restricted'``。
    """
    cfg = db.session.get(AppConfig, app_name)
    return cfg.access_level if cfg else ACCESS_PUBLIC


def has_access(app_name: str) -> bool:
    """判断当前用户是否有权访问指定软件。

    Args:
        app_name: 软件名称。

    Returns:
        ``True`` 表示有权访问，``False`` 表示无权访问。
    """
    level = get_access_level(app_name)

    if level == ACCESS_PUBLIC:
        return True

    if not current_user.is_authenticated:
        return False

    if level == ACCESS_PROTECTED:
        return True

    # restricted：管理员或在授权名单中
    if current_user.is_admin:
        return True
    return AppAccess.query.filter_by(
        app_name=app_name, user_id=current_user.id
    ).first() is not None


def api_check(app_name: str):
    """API 路由访问控制检查。

    在 API 视图函数开头调用，无权时直接返回 JSON 错误响应，有权时返回 None。

    用法::

        err = api_check(app_name)
        if err:
            return err

    Args:
        app_name: 软件名称。

    Returns:
        有权访问时返回 ``None``；无权时返回 ``(Response, status_code)`` 元组，
        其中 Response 为含 ``error`` 键的 JSON。
    """
    level = get_access_level(app_name)

    if level == ACCESS_PUBLIC:
        return None

    if not current_user.is_authenticated:
        return jsonify({'error': '请先登录后访问此软件'}), 401

    if level == ACCESS_PROTECTED:
        return None

    if current_user.is_admin:
        return None

    if AppAccess.query.filter_by(app_name=app_name, user_id=current_user.id).first():
        return None

    return jsonify({'error': '您没有访问此软件的权限'}), 403


def page_check(app_name: str):
    """HTML 页面路由访问控制检查。

    在页面视图函数开头调用，未登录时重定向到登录页，无权时渲染 403 页面，
    有权时返回 None。

    用法::

        err = page_check(app_name)
        if err:
            return err

    Args:
        app_name: 软件名称。

    Returns:
        有权访问时返回 ``None``；未登录时返回登录页重定向响应；
        无权时返回 ``(Response, 403)`` 元组。
    """
    level = get_access_level(app_name)

    if level == ACCESS_PUBLIC:
        return None

    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    if level == ACCESS_PROTECTED:
        return None

    if current_user.is_admin:
        return None

    if AppAccess.query.filter_by(app_name=app_name, user_id=current_user.id).first():
        return None

    return render_template('updatehub/403.html', app_name=app_name), 403