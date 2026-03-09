"""
app/user/views.py - 用户管理蓝图路由。

路由：
    GET       /user/                    用户列表（仅管理员）
    GET/POST  /user/create              创建用户（仅管理员）
    GET/POST  /user/<uid>/edit          编辑用户（管理员可编辑任意用户；普通用户仅限自己）
    POST      /user/<uid>/delete        删除用户（仅管理员，不能删除自己）
    GET       /user/profile             跳转到当前用户编辑页
"""
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.user import user
from app.user.models import User
from app.extensions import db
from app.utils.auth import admin_required


@user.route('/')
@admin_required
def list_users():
    """用户列表页（仅管理员可访问）。

    Returns:
        渲染 ``user/list.html``，传入按创建时间降序排列的用户列表。
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('user/list.html', users=users)


@user.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    """创建新用户（仅管理员可访问）。

    GET : 渲染空白创建表单。
    POST: 校验表单后创建用户并提交数据库，成功后跳转到用户列表。

    Returns:
        成功时重定向到 ``user.list_users``；
        失败时重新渲染 ``user/form.html`` 并通过 flash 显示错误。
    """
    if request.method == 'POST':
        error = _validate_create_form()
        if error:
            flash(error, 'error')
            return render_template('user/form.html', action='create', form=request.form)

        u = User(
            username=request.form['username'].strip(),
            email=request.form.get('email', '').strip() or None,
            role=request.form.get('role', 'user'),
            active=('active' in request.form),
        )
        u.set_password(request.form['password'])
        db.session.add(u)
        db.session.commit()
        flash(f'用户 {u.username} 创建成功', 'success')
        return redirect(url_for('user.list_users'))

    return render_template('user/form.html', action='create', form={})


@user.route('/<int:uid>/edit', methods=['GET', 'POST'])
@login_required
def edit(uid):
    """编辑用户信息。

    管理员可编辑任意用户（含用户名、角色、状态）；
    普通用户只能编辑自己（仅邮箱和密码）。

    Args:
        uid: 目标用户的数据库 ID。

    Returns:
        成功时管理员跳转到 ``user.list_users``，普通用户跳转到 ``user.profile``；
        失败时重新渲染 ``user/form.html``。

    Raises:
        403: 普通用户尝试编辑他人信息时中止。
        404: 目标用户不存在时中止。
    """
    u = User.query.get_or_404(uid)
    # 普通用户只能编辑自己
    if not current_user.is_admin and current_user.id != uid:
        abort(403)

    if request.method == 'POST':
        # 邮箱（所有人可改）
        new_email = request.form.get('email', '').strip() or None
        if new_email and new_email != u.email:
            if User.query.filter(User.email == new_email, User.id != uid).first():
                flash('该邮箱已被其他用户使用', 'error')
                return render_template('user/form.html', action='edit', u=u, form=request.form)
        u.email = new_email

        # 密码（留空则不改）
        new_pw = request.form.get('password', '')
        if new_pw:
            if new_pw != request.form.get('password2', ''):
                flash('两次输入的密码不一致', 'error')
                return render_template('user/form.html', action='edit', u=u, form=request.form)
            u.set_password(new_pw)

        # 以下仅管理员可改
        if current_user.is_admin:
            new_username = request.form.get('username', '').strip()
            if new_username and new_username != u.username:
                if User.query.filter(User.username == new_username, User.id != uid).first():
                    flash('该用户名已存在', 'error')
                    return render_template('user/form.html', action='edit', u=u, form=request.form)
                u.username = new_username
            u.role   = request.form.get('role', 'user')
            u.active = ('active' in request.form)

        db.session.commit()
        flash('用户信息已更新', 'success')
        if current_user.is_admin:
            return redirect(url_for('user.list_users'))
        return redirect(url_for('user.profile'))

    return render_template('user/form.html', action='edit', u=u, form={})


@user.route('/<int:uid>/delete', methods=['POST'])
@admin_required
def delete(uid):
    """删除用户（仅管理员，不能删除当前登录账号）。

    Args:
        uid: 目标用户的数据库 ID。

    Returns:
        重定向到 ``user.list_users``。

    Raises:
        404: 目标用户不存在时中止。
    """
    if uid == current_user.id:
        flash('不能删除当前登录账号', 'error')
        return redirect(url_for('user.list_users'))
    u = User.query.get_or_404(uid)
    db.session.delete(u)
    db.session.commit()
    flash(f'用户 {u.username} 已删除', 'success')
    return redirect(url_for('user.list_users'))


@user.route('/profile')
@login_required
def profile():
    """当前登录用户的个人资料页，重定向到自身编辑页。

    Returns:
        重定向到 ``user.edit``，uid 为当前用户 ID。
    """
    return redirect(url_for('user.edit', uid=current_user.id))


def _validate_create_form():
    """校验创建用户表单数据。

    从 ``request.form`` 读取字段并依次验证：
        - 用户名非空且不超过 64 字符且唯一；
        - 密码非空且两次输入一致；
        - 邮箱（可选）若填写则必须唯一。

    Returns:
        校验通过时返回 ``None``；失败时返回错误描述字符串。
    """
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    password2 = request.form.get('password2', '')

    if not username:
        return '用户名不能为空'
    if len(username) > 64:
        return '用户名不能超过 64 个字符'
    if User.query.filter_by(username=username).first():
        return '该用户名已存在'
    if not password:
        return '密码不能为空'
    if password != password2:
        return '两次输入的密码不一致'
    email = request.form.get('email', '').strip()
    if email and User.query.filter_by(email=email).first():
        return '该邮箱已被使用'
    return None