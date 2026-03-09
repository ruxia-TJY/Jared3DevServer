"""
app/auth/views.py - 认证蓝图路由（登录 / 登出）。

路由：
    GET/POST /auth/login   登录页面及表单处理
    GET      /auth/logout  登出并跳转登录页
"""
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth
from app.user.models import User


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面。

    GET  : 渲染登录表单；已登录用户直接跳转到软件列表页。
    POST : 验证用户名、密码及账号状态，成功后建立会话并跳转。
          失败时以 flash 消息提示错误。

    Returns:
        登录成功时跳转到 ``next`` 参数指定的页面或软件列表页；
        验证失败时重新渲染登录表单。
    """
    if current_user.is_authenticated:
        return redirect(url_for('updatehub.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('updatehub.index'))
        flash('用户名或密码错误', 'error')

    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    """登出当前用户，清除会话并重定向到登录页。

    Returns:
        重定向到 ``auth.login``。
    """
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.login'))