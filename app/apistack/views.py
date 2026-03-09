"""
app/apistack/views.py - API Stack 路由层。

路由总览：

    公开端点（无需登录）：
        GET/POST /apistack/api/<api_name>       执行 API 处理函数
        GET      /apistack/api/doc              API 文档列表页
        GET      /apistack/api/doc/<api_name>   API 详细使用文档（Markdown 渲染）
        GET      /apistack/info/<api_name>      API 元信息（JSON）

    管理端点（仅管理员，@admin_required）：
        GET      /apistack/manage/                      管理列表页
        POST     /apistack/manage/add                   新增 API 条目
        GET/POST /apistack/manage/edit/<api_id>         编辑 API 条目
        POST     /apistack/manage/delete/<api_id>       删除 API 条目
        POST     /apistack/manage/toggle/<api_id>       切换启用/禁用
        POST     /apistack/manage/doc/<api_id>          更新 Markdown 文档
        POST     /apistack/manage/token/add/<api_id>    生成访问 Token
        POST     /apistack/manage/token/delete/<tid>    删除访问 Token

访问控制说明：
    - public  API：任何人可直接调用执行端点。
    - private API：调用执行端点时须携带有效 Token；
                   未登录用户亦无法查看该 API 的文档详情页。
    Token 传入方式（三选一）：
        Header:     X-API-Token: <token>
        Query 参数: ?token=<token>
        JSON body:  {"token": "<token>"}
"""
import secrets

from flask import jsonify, request, render_template, redirect, url_for, flash
from flask_login import current_user

from app.apistack import apistack
from app.apistack.models import ApiEntry, ApiToken
from app.apistack import handlers
from app.extensions import db
from app.utils.auth import admin_required


# ── 文档列表页 ────────────────────────────────────────────────────────────────

@apistack.route('/api/doc')
def api_doc():
    """API 文档列表页。

    根据登录状态过滤可见 API：
        - 未登录：仅显示 visibility='public' 且 enabled=True 的条目。
        - 已登录：显示所有 enabled=True 的条目（包含 private，标注需 Token）。

    Returns:
        Response: 渲染 apistack/doc.html，传入已过滤并按名称排序的 API 列表。
    """
    query = ApiEntry.query.filter_by(enabled=True)
    if not current_user.is_authenticated:
        query = query.filter_by(visibility='public')
    apis = query.order_by(ApiEntry.name).all()
    return render_template('apistack/doc.html', apis=apis)


@apistack.route('/api/doc/<api_name>')
def api_doc_detail(api_name):
    """API 详细使用文档页。

    直接读取预渲染的 doc_html 字段展示，不进行实时 Markdown 转换。
    访问控制：private API 要求登录后才能查看文档内容。

    Args:
        api_name: URL 中的 API 名称，区分大小写，须与 ApiEntry.name 完全匹配。

    Returns:
        Response (200): 渲染 apistack/doc_detail.html。
            - locked=True  : private API 且未登录，显示锁定提示。
            - locked=False : 正常渲染文档（doc_html 可能为 None，届时显示"暂无文档"）。
        Response (404): 指定名称的 API 不存在或已禁用。
    """
    entry = ApiEntry.query.filter_by(name=api_name, enabled=True).first_or_404()

    if entry.visibility == 'private' and not current_user.is_authenticated:
        return render_template('apistack/doc_detail.html', api=entry,
                               doc_html=None, locked=True)

    return render_template('apistack/doc_detail.html', api=entry,
                           doc_html=entry.rendered_doc, locked=False)


# ── API 执行 ──────────────────────────────────────────────────────────────────

@apistack.route('/api/<api_name>', methods=['GET', 'POST'])
def execute_api(api_name):
    """执行指定 API 的处理函数。

    执行流程：
        1. 查找数据库中对应的 ApiEntry；
        2. 检查 enabled 状态；
        3. 若 visibility='private'，校验请求中携带的 Token；
        4. 从 handlers 注册表中查找处理函数并调用。

    Args:
        api_name: URL 中的 API 名称，与 ApiEntry.name 及 handlers 注册名对应。

    Returns:
        Response: 由对应处理函数返回的 Flask Response。
        Response (403): API 已禁用。
        Response (404): API 不存在。
        Response (401): private API 且请求中未携带 Token。
        Response (403): private API 且 Token 无效。
        Response (501): API 已在数据库注册，但处理函数尚未实现。
    """
    entry = ApiEntry.query.filter_by(name=api_name).first()
    if entry is None:
        return jsonify({'error': f'API「{api_name}」不存在'}), 404
    if not entry.enabled:
        return jsonify({'error': f'API「{api_name}」已禁用'}), 403

    if entry.visibility == 'private':
        token = (
            request.headers.get('X-API-Token')
            or request.args.get('token')
            or (request.get_json(silent=True) or {}).get('token')
        )
        if not token:
            return jsonify({'error': '该 API 需要 Token 才能访问'}), 401
        if not ApiToken.query.filter_by(api_id=entry.id, token=token).first():
            return jsonify({'error': '无效的 Token'}), 403

    handler = handlers.get_handler(api_name)
    if handler is None:
        return jsonify({'error': f'API「{api_name}」的处理函数尚未实现'}), 501

    return handler()


# ── API 元信息 ────────────────────────────────────────────────────────────────

@apistack.route('/info/<api_name>')
def api_info(api_name):
    """返回指定 API 的元信息（JSON 格式）。

    响应字段见 ApiEntry.to_dict()。不含 doc_content / doc_html。

    Args:
        api_name: API 名称，区分大小写。

    Returns:
        Response (200): JSON，字段见 ApiEntry.to_dict()。
        Response (404): API 不存在。
    """
    entry = ApiEntry.query.filter_by(name=api_name).first()
    if entry is None:
        return jsonify({'error': f'API「{api_name}」不存在'}), 404
    return jsonify(entry.to_dict())


# ── 管理：列表 ────────────────────────────────────────────────────────────────

@apistack.route('/manage/')
@admin_required
def manage():
    """API 管理列表页（仅管理员）。

    展示所有 API 条目及其 Token 列表，按创建时间降序排列。

    Returns:
        Response: 渲染 apistack/manage.html，传入 apis 列表。
    """
    apis = ApiEntry.query.order_by(ApiEntry.created_at.desc()).all()
    return render_template('apistack/manage.html', apis=apis)


# ── 管理：新增 ────────────────────────────────────────────────────────────────

@apistack.route('/manage/add', methods=['POST'])
@admin_required
def manage_add():
    """新增 API 条目（仅管理员）。

    从表单读取字段，校验 name 唯一性后写入数据库。
    若提供了 doc_content，同时调用 render_doc() 生成预渲染 HTML。

    Form 字段：
        name         (str, 必填): URL slug，区分大小写，全局唯一。
        display_name (str, 必填): 显示名称。
        description  (str, 可选): 一句话描述。
        author       (str, 可选): 作者名。
        version      (str, 可选): 版本号，默认 "1.0.0"。
        visibility   (str, 可选): "public"（默认）或 "private"。
        doc_content  (str, 可选): Markdown 文档内容。

    Returns:
        Response: 重定向到 apistack.manage；通过 flash 传递操作结果。
    """
    name         = request.form.get('name', '').strip()
    display_name = request.form.get('display_name', '').strip()
    description  = request.form.get('description', '').strip()
    author       = request.form.get('author', '').strip()
    version      = request.form.get('version', '1.0.0').strip()
    visibility   = request.form.get('visibility', 'public')
    doc_content  = request.form.get('doc_content', '').strip()

    if not name or not display_name:
        flash('名称和显示名称为必填项', 'error')
        return redirect(url_for('apistack.manage'))

    if visibility not in ('public', 'private'):
        visibility = 'public'

    if ApiEntry.query.filter_by(name=name).first():
        flash(f'API「{name}」已存在', 'error')
        return redirect(url_for('apistack.manage'))

    entry = ApiEntry(
        name=name,
        display_name=display_name,
        description=description or None,
        author=author or None,
        version=version or '1.0.0',
        visibility=visibility,
        doc_content=doc_content or None,
    )
    entry.render_doc()  # 写时渲染，读时直取
    db.session.add(entry)
    db.session.commit()
    flash(f'API「{name}」添加成功', 'success')
    return redirect(url_for('apistack.manage'))


# ── 管理：编辑 ────────────────────────────────────────────────────────────────

@apistack.route('/manage/edit/<int:api_id>', methods=['GET', 'POST'])
@admin_required
def manage_edit(api_id):
    """编辑 API 条目的元信息与文档（仅管理员）。

    GET：渲染编辑表单，预填当前值。
    POST：更新字段并触发文档重新渲染后写库。
    注意：name（URL slug）字段不允许修改，表单中仅作只读展示。

    Args:
        api_id: ApiEntry 主键。

    Form 字段（POST）：
        display_name (str): 显示名称。
        description  (str): 一句话描述，留空则置 None。
        author       (str): 作者名，留空则置 None。
        version      (str): 版本号。
        visibility   (str): "public" 或 "private"。
        enabled      (str): "1" 表示启用，其他值表示禁用。
        doc_content  (str): Markdown 文档，留空则置 None 并清空 doc_html。

    Returns:
        GET  Response: 渲染 apistack/edit.html。
        POST Response: 重定向到 apistack.manage；通过 flash 传递结果。
        Response (redirect+flash): api_id 不存在时重定向并提示错误。
    """
    entry = db.session.get(ApiEntry, api_id)
    if entry is None:
        flash('API 不存在', 'error')
        return redirect(url_for('apistack.manage'))

    if request.method == 'POST':
        entry.display_name = request.form.get('display_name', '').strip() or entry.display_name
        entry.description  = request.form.get('description', '').strip() or None
        entry.author       = request.form.get('author', '').strip() or None
        entry.version      = request.form.get('version', '').strip() or entry.version
        entry.visibility   = request.form.get('visibility', entry.visibility)
        entry.enabled      = request.form.get('enabled') == '1'
        entry.doc_content  = request.form.get('doc_content', '').strip() or None
        if entry.visibility not in ('public', 'private'):
            entry.visibility = 'public'
        entry.render_doc()  # 写时渲染，读时直取
        db.session.commit()
        flash(f'API「{entry.name}」已更新', 'success')
        return redirect(url_for('apistack.manage'))

    return render_template('apistack/edit.html', api=entry)


# ── 管理：删除 ────────────────────────────────────────────────────────────────

@apistack.route('/manage/delete/<int:api_id>', methods=['POST'])
@admin_required
def manage_delete(api_id):
    """删除 API 条目及其关联的所有 Token（仅管理员）。

    Args:
        api_id: ApiEntry 主键。

    Returns:
        Response: 重定向到 apistack.manage；通过 flash 传递操作结果。
    """
    entry = db.session.get(ApiEntry, api_id)
    if entry is None:
        flash('API 不存在', 'error')
        return redirect(url_for('apistack.manage'))
    name = entry.name
    db.session.delete(entry)
    db.session.commit()
    flash(f'API「{name}」已删除', 'success')
    return redirect(url_for('apistack.manage'))


# ── 管理：启用/禁用 ───────────────────────────────────────────────────────────

@apistack.route('/manage/toggle/<int:api_id>', methods=['POST'])
@admin_required
def manage_toggle(api_id):
    """切换 API 的启用/禁用状态（仅管理员）。

    禁用后调用执行端点将返回 403；文档页仍可正常访问。

    Args:
        api_id: ApiEntry 主键。

    Returns:
        Response: 重定向到 apistack.manage；通过 flash 传递操作结果。
    """
    entry = db.session.get(ApiEntry, api_id)
    if entry is None:
        flash('API 不存在', 'error')
        return redirect(url_for('apistack.manage'))
    entry.enabled = not entry.enabled
    db.session.commit()
    state = '启用' if entry.enabled else '禁用'
    flash(f'API「{entry.name}」已{state}', 'info')
    return redirect(url_for('apistack.manage'))


# ── 管理：文档更新 ────────────────────────────────────────────────────────────

@apistack.route('/manage/doc/<int:api_id>', methods=['POST'])
@admin_required
def manage_doc(api_id):
    """更新 API 的 Markdown 使用文档（仅管理员）。

    保存 doc_content 后立即调用 render_doc() 将其渲染为 HTML，
    后续读取文档时直接使用预渲染结果，无实时计算开销。

    Args:
        api_id: ApiEntry 主键。

    Form 字段：
        doc_content (str): Markdown 文档内容，留空则清除文档。

    Returns:
        Response: 重定向到 apistack.manage；通过 flash 传递操作结果。
    """
    entry = db.session.get(ApiEntry, api_id)
    if entry is None:
        flash('API 不存在', 'error')
        return redirect(url_for('apistack.manage'))
    entry.doc_content = request.form.get('doc_content', '').strip() or None
    entry.render_doc()  # 写时渲染，读时直取
    db.session.commit()
    flash(f'API「{entry.name}」文档已更新', 'success')
    return redirect(url_for('apistack.manage'))


# ── 管理：Token ───────────────────────────────────────────────────────────────

@apistack.route('/manage/token/add/<int:api_id>', methods=['POST'])
@admin_required
def manage_token_add(api_id):
    """为私有 API 生成新的访问 Token（仅管理员）。

    Token 由 secrets.token_hex(24) 生成，长度 48 个十六进制字符，全表唯一。
    生成后通过 flash 一次性展示，之后无法再次查看，请妥善保存。

    Args:
        api_id: ApiEntry 主键。

    Form 字段：
        label (str, 可选): 使用方备注，如"iOS 客户端"。

    Returns:
        Response: 重定向到 apistack.manage；flash 中包含完整 Token 字符串。
    """
    entry = db.session.get(ApiEntry, api_id)
    if entry is None:
        flash('API 不存在', 'error')
        return redirect(url_for('apistack.manage'))
    label = request.form.get('label', '').strip() or None
    token = secrets.token_hex(24)
    db.session.add(ApiToken(api_id=entry.id, token=token, label=label))
    db.session.commit()
    flash(f'Token 已生成，请妥善保存：{token}', 'success')
    return redirect(url_for('apistack.manage'))


@apistack.route('/manage/token/delete/<int:token_id>', methods=['POST'])
@admin_required
def manage_token_delete(token_id):
    """删除指定的访问 Token（仅管理员）。

    删除后持有该 Token 的使用方将立即失去访问权限。

    Args:
        token_id: ApiToken 主键。

    Returns:
        Response: 重定向到 apistack.manage；通过 flash 传递操作结果。
    """
    tok = db.session.get(ApiToken, token_id)
    if tok is None:
        flash('Token 不存在', 'error')
        return redirect(url_for('apistack.manage'))
    db.session.delete(tok)
    db.session.commit()
    flash('Token 已删除', 'success')
    return redirect(url_for('apistack.manage'))