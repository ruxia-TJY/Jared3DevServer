"""
app/utils/db_helpers.py - 数据库常用查询与写入辅助函数。

提供：
    get_latest_row  - 查询某软件某平台的最新版本记录
    get_latest_dict - 查询某软件各平台最新版本号字典
    upsert_version  - 插入或更新版本记录
"""
from packaging.version import Version, InvalidVersion
import config
from app.extensions import db
from app.updatehub.models import AppVersion


def get_latest_row(app_name: str, platform: str):
    """查询指定软件在指定平台的最新版本记录。

    使用 ``packaging.version.Version`` 进行语义化版本比较；
    若版本号格式异常则退化为按数据库插入顺序取最后一条。

    Args:
        app_name: 软件名称。
        platform: 平台标识符（``'windows'`` / ``'mac'`` / ``'linux'``）。

    Returns:
        最新的 ``AppVersion`` 实例；若该平台无任何记录则返回 ``None``。
    """
    rows = AppVersion.query.filter_by(app_name=app_name, platform=platform).all()
    if not rows:
        return None
    try:
        return max(rows, key=lambda r: Version(r.version))
    except InvalidVersion:
        return rows[-1]


def get_latest_dict(app_name: str) -> dict:
    """返回指定软件各平台最新版本号的映射字典。

    Args:
        app_name: 软件名称。

    Returns:
        以平台标识符为键、版本号字符串为值的字典，例如::

            {"windows": "1.2.0", "linux": "1.1.0"}

        无版本的平台不会出现在结果中。
    """
    result = {}
    for platform in config.ALLOWED_PLATFORMS:
        row = get_latest_row(app_name, platform)
        if row:
            result[platform] = row.version
    return result


def upsert_version(app_name: str, version: str, platform: str, fields: dict) -> AppVersion:
    """插入或更新软件版本记录，并自动提交事务。

    若 ``(app_name, version, platform)`` 组合已存在则更新字段，否则插入新行。

    Args:
        app_name: 软件名称。
        version : 版本号字符串，须符合 PEP 440 规范。
        platform: 平台标识符。
        fields  : 待写入的字段字典，键名对应 ``AppVersion`` 的列名。

    Returns:
        已持久化的 ``AppVersion`` 实例。
    """
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
