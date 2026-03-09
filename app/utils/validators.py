import re
from packaging.version import Version, InvalidVersion
import config


def is_valid_app_name(name: str) -> bool:
    """软件名称只允许字母、数字、下划线和连字符。"""
    return bool(re.match(r'^[a-zA-Z0-9_\-]+$', name))


def is_valid_version(v: str) -> bool:
    """版本号须符合 PEP 440 规范。"""
    try:
        Version(v)
        return True
    except InvalidVersion:
        return False


def is_valid_platform(platform: str) -> bool:
    return platform in config.ALLOWED_PLATFORMS


def file_extension_allowed(platform: str, filename: str) -> bool:
    """检查上传文件的扩展名是否在该平台的白名单内。"""
    import os
    if filename.endswith('.tar.gz'):
        ext = '.tar.gz'
    else:
        _, ext = os.path.splitext(filename)
    return ext.lower() in config.ALLOWED_EXTENSIONS.get(platform, set())
