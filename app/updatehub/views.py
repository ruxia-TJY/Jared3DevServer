"""
app/updatehub/views.py - updatehub 蓝图所有路由。

API 端点（JSON）：
    GET  /api/apps                          列出所有软件
    GET  /api/<app>/latest                  最新版本
    GET  /api/<app>/versions                所有版本
    GET  /api/<app>/check                   更新检查
    GET  /api/<app>/download                下载文件
    POST /api/<app>/upload          [Token] 上传本地版本
    POST /api/<app>/register        [Token] 注册 GitHub Release
    DEL  /api/<app>/delete          [Token] 删除版本
    GET  /api/<app>/access          [Token] 查询访问配置
    POST /api/<app>/access          [Token] 修改访问级别
    POST /api/<app>/access/users    [Token] 授权用户
    DEL  /api/<app>/access/users/<id>[Token] 撤销授权

HTML 页面：
    GET  /          软件列表（按访问级别分组）
    GET  /<app>     软件详情（版本列表、SHA256、下载）
"""
import os
from datetime import date

import requests as http_requests
from flask import (
    request, jsonify, render_template, send_from_directory,
    redirect, abort, Response, stream_with_context,
)
from packaging.version import Version, InvalidVersion
from werkzeug.utils import secure_filename

from app.updatehub import updatehub
from app.updatehub.models import AppVersion, AppConfig, AppAccess, ACCESS_PUBLIC, ACCESS_PROTECTED, ACCESS_RESTRICTED
from app.updatehub.access import api_check, page_check, get_access_level, has_access
from app.extensions import db
from app.user.models import User
from app.utils.auth import require_token
from app.utils.validators import (
    is_valid_app_name, is_valid_version, is_valid_platform, file_extension_allowed,
)
from app.utils.file_utils import sha256_of_file
from app.utils.db_helpers import get_latest_row, get_latest_dict, upsert_version
import config


# ── 软件列表 ────────────────────────────────────────────────

@updatehub.route('/api/apps', methods=['GET'])
def list_apps():
    """列出所有软件及各平台最新版本。"""
    rows = db.session.query(AppVersion.app_name).distinct().all()
    result = []
    for (app_name,) in rows:
        count = AppVersion.query.filter_by(app_name=app_name).count()
        result.append({
            'app':           app_name,
            'latest':        get_latest_dict(app_name),
            'version_count': count,
        })
    return jsonify({'apps': result})


# ── 版本查询 ────────────────────────────────────────────────

@updatehub.route('/api/<app_name>/latest', methods=['GET'])
def get_latest(app_name):
    """
    获取指定软件的最新版本信息。
    Query: platform=windows|mac|linux （可选，不传则返回所有平台）
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    err = api_check(app_name)
    if err:
        return err

    if not AppVersion.query.filter_by(app_name=app_name).first():
        return jsonify({'error': '软件不存在'}), 404

    platform = request.args.get('platform', '').lower()

    if platform:
        if not is_valid_platform(platform):
            return jsonify({'error': f'不支持的平台，可选：{", ".join(config.ALLOWED_PLATFORMS)}'}), 400
        row = get_latest_row(app_name, platform)
        if not row:
            return jsonify({'error': '该平台暂无版本'}), 404
        return jsonify({'app': app_name, **row.to_dict(app_name)})

    result = {}
    for plat in config.ALLOWED_PLATFORMS:
        row = get_latest_row(app_name, plat)
        if row:
            result[plat] = row.to_dict(app_name)
    return jsonify({'app': app_name, 'latest': result})


@updatehub.route('/api/<app_name>/versions', methods=['GET'])
def list_versions(app_name):
    """列出某软件的所有版本及详细信息。"""
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    err = api_check(app_name)
    if err:
        return err

    if not AppVersion.query.filter_by(app_name=app_name).first():
        return jsonify({'error': '软件不存在'}), 404

    rows = AppVersion.query.filter_by(app_name=app_name).order_by(
        AppVersion.version.desc(), AppVersion.platform
    ).all()

    versions = {}
    for row in rows:
        versions.setdefault(row.version, {})[row.platform] = row.to_dict()

    return jsonify({
        'app':      app_name,
        'latest':   get_latest_dict(app_name),
        'versions': versions,
    })


@updatehub.route('/api/<app_name>/check', methods=['GET'])
def check_update(app_name):
    """
    检查是否有新版本。
    Query: platform=windows|mac|linux  &  version=1.0.0
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    err = api_check(app_name)
    if err:
        return err

    platform        = request.args.get('platform', '').lower()
    current_version = request.args.get('version', '')

    if not is_valid_platform(platform):
        return jsonify({'error': f'不支持的平台，可选：{", ".join(config.ALLOWED_PLATFORMS)}'}), 400
    if not is_valid_version(current_version):
        return jsonify({'error': '版本号格式不正确'}), 400

    if not AppVersion.query.filter_by(app_name=app_name).first():
        return jsonify({'error': '软件不存在'}), 404

    latest_row = get_latest_row(app_name, platform)
    if not latest_row:
        return jsonify({'has_update': False, 'message': '该平台暂无版本'})

    try:
        has_update = Version(latest_row.version) > Version(current_version)
    except InvalidVersion:
        return jsonify({'error': '服务器版本数据异常'}), 500

    response = {'has_update': has_update, 'latest_version': latest_row.version}
    if has_update:
        response.update(latest_row.to_dict(app_name))
    return jsonify(response)


# ── 下载 ────────────────────────────────────────────────────

@updatehub.route('/api/<app_name>/download', methods=['GET'])
def download_update(app_name):
    """
    下载指定版本。
    Query: platform=windows|mac|linux  &  version=1.0.1
    行为由版本元数据中的 source 字段决定：
      - local        : 直接返回服务器本地文件
      - github       : 302 重定向到 GitHub Release 原始地址
      - github_proxy : 服务器从 GitHub 拉取后流式中转给客户端
    """
    if not is_valid_app_name(app_name):
        abort(400)

    err = api_check(app_name)
    if err:
        return err

    platform = request.args.get('platform', '').lower()
    version  = request.args.get('version', '')

    if not is_valid_platform(platform):
        abort(400)
    if not is_valid_version(version):
        abort(400)

    row = AppVersion.query.filter_by(
        app_name=app_name, version=version, platform=platform
    ).first()
    if not row:
        abort(404)

    if row.source == 'github':
        if not row.github_url:
            abort(404)
        return redirect(row.github_url, code=302)

    if row.source == 'github_proxy':
        if not row.github_url:
            abort(404)
        github_url = row.github_url
        filename   = github_url.split('/')[-1] or f"{app_name}-{version}-{platform}"

        def generate():
            with http_requests.get(github_url, stream=True, timeout=30) as r:
                if r.status_code != 200:
                    abort(502)
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk

        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type':        'application/octet-stream',
        }
        try:
            probe = http_requests.head(github_url, timeout=10, allow_redirects=True)
            content_length = probe.headers.get('Content-Length')
            if content_length:
                headers['Content-Length'] = content_length
        except Exception:
            pass
        return Response(stream_with_context(generate()), headers=headers)

    # source == 'local'
    directory = os.path.join(config.UPLOAD_FOLDER, app_name, platform)
    if not row.filename:
        return jsonify({'error': '文件记录不完整，缺少文件名'}), 404
    if not os.path.exists(os.path.join(directory, row.filename)):
        return jsonify({'error': f'文件不存在于服务器：{row.filename}，请重新上传'}), 404
    return send_from_directory(directory, row.filename, as_attachment=True)


# ── 管理（需要 Token）──────────────────────────────────────

@updatehub.route('/api/<app_name>/upload', methods=['POST'])
@require_token
def upload_update(app_name):
    """
    上传本地文件版本（需要 Token）。
    Form fields:
      - platform     : windows | mac | linux
      - version      : 1.0.1
      - file         : 安装包文件
      - release_notes: 更新说明（可选）
      - mandatory    : true | false，默认 false（可选）
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    platform      = request.form.get('platform', '').lower()
    version       = request.form.get('version', '').strip()
    release_notes = request.form.get('release_notes', '')
    mandatory     = request.form.get('mandatory', 'false').lower() == 'true'

    if not is_valid_platform(platform):
        return jsonify({'error': f'不支持的平台，可选：{", ".join(config.ALLOWED_PLATFORMS)}'}), 400
    if not is_valid_version(version):
        return jsonify({'error': '版本号格式不正确（示例：1.0.0）'}), 400

    if 'file' not in request.files:
        return jsonify({'error': '未找到上传文件（字段名应为 file）'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'error': '文件名为空'}), 400
    if not file_extension_allowed(platform, f.filename):
        allowed = ', '.join(config.ALLOWED_EXTENSIONS[platform])
        return jsonify({'error': f'不支持的文件类型，{platform} 平台允许：{allowed}'}), 400

    if f.filename.endswith('.tar.gz'):
        ext = '.tar.gz'
    else:
        _, ext = os.path.splitext(f.filename)
    safe_filename = secure_filename(f"{app_name}-{version}-{platform}{ext}")

    save_dir  = os.path.join(config.UPLOAD_FOLDER, app_name, platform)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, safe_filename)
    f.save(save_path)

    file_size = os.path.getsize(save_path)
    sha256    = sha256_of_file(save_path)

    upsert_version(app_name, version, platform, {
        'source':        'local',
        'filename':      safe_filename,
        'github_url':    None,
        'file_size':     file_size,
        'sha256':        sha256,
        'release_notes': release_notes,
        'release_date':  date.today(),
        'mandatory':     mandatory,
    })

    return jsonify({
        'success':   True,
        'app':       app_name,
        'version':   version,
        'platform':  platform,
        'filename':  safe_filename,
        'file_size': file_size,
        'sha256':    sha256,
    }), 201


@updatehub.route('/api/<app_name>/register', methods=['POST'])
@require_token
def register_github(app_name):
    """
    注册 GitHub Release 版本（需要 Token）。
    JSON body:
      {
        "platform":      "windows",
        "version":       "1.0.1",
        "github_url":    "https://github.com/user/repo/releases/download/v1.0.1/app.exe",
        "source":        "github_proxy",
        "release_notes": "...",
        "mandatory":     false,
        "file_size":     12345678,
        "sha256":        "abc123..."
      }
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    body          = request.get_json(silent=True) or {}
    platform      = body.get('platform', '').lower()
    version       = body.get('version', '').strip()
    github_url    = body.get('github_url', '').strip()
    source        = body.get('source', 'github_proxy')
    release_notes = body.get('release_notes', '')
    mandatory     = bool(body.get('mandatory', False))
    file_size     = body.get('file_size', 0)
    sha256        = body.get('sha256', '')

    if not is_valid_platform(platform):
        return jsonify({'error': f'不支持的平台，可选：{", ".join(config.ALLOWED_PLATFORMS)}'}), 400
    if not is_valid_version(version):
        return jsonify({'error': '版本号格式不正确（示例：1.0.0）'}), 400
    if source not in ('github', 'github_proxy'):
        return jsonify({'error': 'source 必须为 github 或 github_proxy'}), 400
    if not github_url.startswith('https://github.com/'):
        return jsonify({'error': 'github_url 必须以 https://github.com/ 开头'}), 400

    upsert_version(app_name, version, platform, {
        'source':        source,
        'filename':      None,
        'github_url':    github_url,
        'file_size':     file_size,
        'sha256':        sha256,
        'release_notes': release_notes,
        'release_date':  date.today(),
        'mandatory':     mandatory,
    })

    return jsonify({
        'success':    True,
        'app':        app_name,
        'version':    version,
        'platform':   platform,
        'source':     source,
        'github_url': github_url,
    }), 201


@updatehub.route('/api/<app_name>/delete', methods=['DELETE'])
@require_token
def delete_version(app_name):
    """
    删除指定版本（需要 Token）。
    Query: platform=windows|mac|linux  &  version=1.0.0
    local 来源同时删除服务器上的安装包文件；github/github_proxy 仅删除数据库记录。
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    platform = request.args.get('platform', '').lower()
    version  = request.args.get('version', '')

    if not is_valid_platform(platform):
        return jsonify({'error': '不支持的平台'}), 400
    if not is_valid_version(version):
        return jsonify({'error': '版本号格式不正确'}), 400

    row = AppVersion.query.filter_by(
        app_name=app_name, version=version, platform=platform
    ).first()
    if not row:
        return jsonify({'error': '版本不存在'}), 404

    if row.source == 'local' and row.filename:
        file_path = os.path.join(config.UPLOAD_FOLDER, app_name, platform, row.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(row)
    db.session.commit()

    return jsonify({'success': True, 'message': f'{app_name} v{version} ({platform}) 已删除'})


# ── HTML 页面 ───────────────────────────────────────────────

@updatehub.route('/', methods=['GET'])
def index():
    """软件列表页。按访问级别分组，仅展示当前用户有权访问的软件。"""
    app_names = [r[0] for r in db.session.query(AppVersion.app_name).distinct().all()]

    groups = {'public': [], 'protected': [], 'restricted': []}
    for name in sorted(app_names):
        level = get_access_level(name)
        if not has_access(name):
            continue
        count = AppVersion.query.filter_by(app_name=name).count()
        groups[level].append({
            'name':          name,
            'latest':        get_latest_dict(name),
            'version_count': count,
            'access_level':  level,
        })

    total = sum(len(v) for v in groups.values())
    return render_template('updatehub/index.html', groups=groups, total=total)


@updatehub.route('/<app_name>', methods=['GET'])
def app_detail(app_name):
    """软件详情页，展示所有版本信息。"""
    if not is_valid_app_name(app_name):
        return render_template('updatehub/404.html'), 404

    if not AppVersion.query.filter_by(app_name=app_name).first():
        return render_template('updatehub/404.html'), 404

    err = page_check(app_name)
    if err:
        return err

    latest = {}
    for plat in config.ALLOWED_PLATFORMS:
        row = get_latest_row(app_name, plat)
        if row:
            latest[plat] = row.to_dict(app_name)

    rows = AppVersion.query.filter_by(app_name=app_name).order_by(
        AppVersion.release_date.desc(), AppVersion.version.desc()
    ).all()

    versions = {}
    for row in rows:
        versions.setdefault(row.version, {})[row.platform] = row.to_dict(app_name)

    return render_template('updatehub/app_detail.html',
                           app_name=app_name,
                           latest=latest,
                           versions=versions,
                           platforms=sorted(config.ALLOWED_PLATFORMS),
                           access_level=get_access_level(app_name))


# ── 访问控制管理（需要 Token）──────────────────────────────

@updatehub.route('/api/<app_name>/access', methods=['GET'])
@require_token
def get_access(app_name):
    """获取软件访问控制配置及授权用户列表。"""
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    level = get_access_level(app_name)
    users = []
    if level == ACCESS_RESTRICTED:
        rows = AppAccess.query.filter_by(app_name=app_name).all()
        users = [{'user_id': r.user_id, 'username': r.user.username} for r in rows]

    return jsonify({'app': app_name, 'access_level': level, 'users': users})


@updatehub.route('/api/<app_name>/access', methods=['POST'])
@require_token
def set_access(app_name):
    """
    设置软件访问级别。
    JSON body: {"access_level": "public" | "protected" | "restricted"}
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    body  = request.get_json(silent=True) or {}
    level = body.get('access_level', '')

    if level not in (ACCESS_PUBLIC, ACCESS_PROTECTED, ACCESS_RESTRICTED):
        return jsonify({'error': f'access_level 必须为 public / protected / restricted'}), 400

    cfg = db.session.get(AppConfig, app_name)
    if cfg is None:
        cfg = AppConfig(app_name=app_name)
        db.session.add(cfg)
    cfg.access_level = level
    db.session.commit()

    return jsonify({'success': True, 'app': app_name, 'access_level': level})


@updatehub.route('/api/<app_name>/access/users', methods=['POST'])
@require_token
def grant_access(app_name):
    """
    授权用户访问 restricted 软件。
    JSON body: {"username": "john"}  或  {"user_id": 1}
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    body = request.get_json(silent=True) or {}
    user = None
    if 'user_id' in body:
        user = db.session.get(User, body['user_id'])
    elif 'username' in body:
        user = User.query.filter_by(username=body['username']).first()

    if not user:
        return jsonify({'error': '用户不存在'}), 404

    if AppAccess.query.filter_by(app_name=app_name, user_id=user.id).first():
        return jsonify({'message': '该用户已有访问权限'}), 200

    db.session.add(AppAccess(app_name=app_name, user_id=user.id))
    db.session.commit()

    return jsonify({'success': True, 'app': app_name, 'username': user.username}), 201


@updatehub.route('/api/<app_name>/access/users/<int:user_id>', methods=['DELETE'])
@require_token
def revoke_access(app_name, user_id):
    """撤销用户对 restricted 软件的访问权限。"""
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

    row = AppAccess.query.filter_by(app_name=app_name, user_id=user_id).first()
    if not row:
        return jsonify({'error': '该用户无此软件的访问权限'}), 404

    db.session.delete(row)
    db.session.commit()

    return jsonify({'success': True, 'app': app_name, 'user_id': user_id})