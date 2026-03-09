"""
app/utils/file_utils.py - 文件操作辅助函数。

提供：
    sha256_of_file  - 以流式方式计算大文件的 SHA256 哈希值
"""
import hashlib


def sha256_of_file(path: str) -> str:
    """以流式方式计算文件的 SHA256 校验值。

    以 64 KB 为块大小分批读取文件，适用于大型安装包，避免一次性加载到内存。

    Args:
        path: 文件的绝对路径或相对路径。

    Returns:
        64 位小写十六进制 SHA256 哈希字符串。

    Raises:
        FileNotFoundError: 指定路径的文件不存在。
        IOError: 文件读取失败。
    """
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()
