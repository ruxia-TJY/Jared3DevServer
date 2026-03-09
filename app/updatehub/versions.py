from flask import request, jsonify
from packaging.version import Version, InvalidVersion
from app.updatehub import updatehub
from app.models import AppVersion
from app.utils.validators import is_valid_app_name, is_valid_version, is_valid_platform
from app.utils.db_helpers import get_latest_row, get_latest_dict
import config


@updatehub.route('/api/<app_name>/latest', methods=['GET'])
def get_latest(app_name):
    """
    获取指定软件的最新版本信息。
    Query: platform=windows|mac|linux （可选，不传则返回所有平台）
    """
    if not is_valid_app_name(app_name):
        return jsonify({'error': '非法的软件名称'}), 400

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
