import hashlib


def sha256_of_file(path: str) -> str:
    """计算文件的 SHA256 校验值。"""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()
