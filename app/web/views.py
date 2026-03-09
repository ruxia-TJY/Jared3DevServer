from flask import render_template
from app.web import web
from app.extensions import db
from app.models import AppVersion
from app.utils.validators import is_valid_app_name
from app.utils.db_helpers import get_latest_row, get_latest_dict
import config


@web.route('/', methods=['GET'])
def index():
    """软件列表页。"""
    app_names = [r[0] for r in db.session.query(AppVersion.app_name).distinct().all()]
    apps = []
    for name in sorted(app_names):
        count = AppVersion.query.filter_by(app_name=name).count()
        apps.append({
            'name':          name,
            'latest':        get_latest_dict(name),
            'version_count': count,
        })
    return render_template('index.html', apps=apps)


@web.route('/<app_name>', methods=['GET'])
def app_detail(app_name):
    """软件详情页，展示所有版本信息。"""
    if not is_valid_app_name(app_name):
        return render_template('404.html'), 404

    if not AppVersion.query.filter_by(app_name=app_name).first():
        return render_template('404.html'), 404

    # 各平台最新版本
    latest = {}
    for plat in config.ALLOWED_PLATFORMS:
        row = get_latest_row(app_name, plat)
        if row:
            latest[plat] = row.to_dict(app_name)

    # 全部版本（按版本号倒序）
    rows = AppVersion.query.filter_by(app_name=app_name).order_by(
        AppVersion.release_date.desc(), AppVersion.version.desc()
    ).all()

    # 整理为 {version: {platform: info}} 结构
    versions = {}
    for row in rows:
        versions.setdefault(row.version, {})[row.platform] = row.to_dict(app_name)

    return render_template('app_detail.html',
                           app_name=app_name,
                           latest=latest,
                           versions=versions,
                           platforms=sorted(config.ALLOWED_PLATFORMS))