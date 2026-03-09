from flask import jsonify
from app.updatehub import updatehub
from app.extensions import db
from app.models import AppVersion
from app.utils.db_helpers import get_latest_dict


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
