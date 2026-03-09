from packaging.version import Version, InvalidVersion
import config
from app.extensions import db
from app.models import AppVersion


def get_latest_row(app_name: str, platform: str):
    """返回指定软件+平台的最新版本行，若无记录则返回 None。"""
    rows = AppVersion.query.filter_by(app_name=app_name, platform=platform).all()
    if not rows:
        return None
    try:
        return max(rows, key=lambda r: Version(r.version))
    except InvalidVersion:
        return rows[-1]


def get_latest_dict(app_name: str) -> dict:
    """返回该软件各平台最新版本号的字典，用于 API 响应。"""
    result = {}
    for platform in config.ALLOWED_PLATFORMS:
        row = get_latest_row(app_name, platform)
        if row:
            result[platform] = row.version
    return result


def upsert_version(app_name: str, version: str, platform: str, fields: dict) -> AppVersion:
    """插入或更新一条版本记录并提交事务。"""
    row = AppVersion.query.filter_by(
        app_name=app_name, version=version, platform=platform
    ).first()
    if row is None:
        row = AppVersion(app_name=app_name, version=version, platform=platform)
        db.session.add(row)
    for key, val in fields.items():
        setattr(row, key, val)
    db.session.commit()
    return row
