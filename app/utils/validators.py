"""
app/utils/validators.py - 输入校验工具函数。

提供：
    is_valid_app_name       - 校验软件名称格式
    is_valid_version        - 校验版本号是否符合 PEP 440
    is_valid_platform       - 校验平台标识符是否在允许列表中
    file_extension_allowed  - 校验上传文件扩展名是否在平台白名单内
"""
import re
from packaging.version import Version, InvalidVersion
import config


def is_valid_app_name(name: str) -> bool:
    """校验软件名称格式。

    只允许 ASCII 字母、数字、下划线（``_``）和连字符（``-``），不允许空格或特殊符号。

    Args:
        name: 待校验的软件名称字符串。

    Returns:
        格式合法时返回 ``True``，否则返回 ``False``。
    """
    return bool(re.match(r'^[a-zA-Z0-9_\-]+$', name))


def is_valid_version(v: str) -> bool:
    """校验版本号是否符合 PEP 440 规范。

    Args:
        v: 待校验的版本号字符串，例如 ``'1.0.0'``、``'2.3.1a1'``。

    Returns:
        合法时返回 ``True``，否则返回 ``False``。
    """
    try:
        Version(v)
        return True
    except InvalidVersion:
        return False


def is_valid_platform(platform: str) -> bool:
    """校验平台标识符是否在允许列表中。

    允许的平台由 ``config.ALLOWED_PLATFORMS`` 定义（默认为 ``windows``、``mac``、``linux``）。

    Args:
        platform: 待校验的平台字符串。

    Returns:
        在允许列表中时返回 ``True``，否则返回 ``False``。
    """
    return platform in config.ALLOWED_PLATFORMS


def file_extension_allowed(platform: str, filename: str) -> bool:
    """校验上传文件的扩展名是否在指定平台的白名单内。

    特殊处理 ``.tar.gz`` 双扩展名，避免被 ``os.path.splitext`` 截断为 ``.gz``。

    Args:
        platform: 平台标识符（``'windows'`` / ``'mac'`` / ``'linux'``）。
        filename: 上传文件的原始文件名。

    Returns:
        扩展名在白名单内时返回 ``True``，否则返回 ``False``。
    """
    import os
    if filename.endswith('.tar.gz'):
        ext = '.tar.gz'
    else:
        _, ext = os.path.splitext(filename)
    return ext.lower() in config.ALLOWED_EXTENSIONS.get(platform, set())
