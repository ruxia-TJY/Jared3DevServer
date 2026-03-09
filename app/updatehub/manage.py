import os
from datetime import date
from flask import request, jsonify
from werkzeug.utils import secure_filename
from app.updatehub import updatehub
from app.extensions import db
from app.models import AppVersion
from app.utils.auth import require_token
from app.utils.validators import (
    is_valid_app_name, is_valid_version, is_valid_platform, file_extension_allowed
)
from app.utils.file_utils import sha256_of_file
from app.utils.db_helpers import upsert_version
import config


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

    # 生成安全的存储文件名：appname-version-platform.ext
    if f.filename.endswith('.tar.gz'):
        ext = '.tar.gz'
    else:
        import os as _os
        _, ext = _os.path.splitext(f.filename)
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
        "source":        "github_proxy",  // "github"（重定向）或 "github_proxy"（中转），默认 github_proxy
        "release_notes": "...",           // 可选
        "mandatory":     false,           // 可选
        "file_size":     12345678,        // 可选
        "sha256":        "abc123..."      // 可选
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

    # local 来源：同时删除本地文件
    if row.source == 'local' and row.filename:
        file_path = os.path.join(config.UPLOAD_FOLDER, app_name, platform, row.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(row)
    db.session.commit()

    return jsonify({'success': True, 'message': f'{app_name} v{version} ({platform}) 已删除'})
