"""
config.py - Jared3Dev Server 全局配置。

使用说明：
    1. 复制 .env.example 为 .env，填入真实的数据库密码后启动；
    2. 上传 Token 与 Session 密钥在首次运行时自动生成，
       分别持久化至 data/.token 和 data/.secret_key；
    3. .env 已加入 .gitignore，数据库密码等敏感信息不会提交到版本库。

运行时自动创建的文件：
    data/.token       - 文件上传接口的鉴权 Token（64 位十六进制）
    data/.secret_key  - Flask Session 加密密钥（64 位十六进制）
"""
import os
import secrets
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()  # 从 .env 文件加载环境变量（不覆盖系统已有的同名变量）

# ── 项目名称 ────────────────────────────────────────────────
APP_NAME = 'Jared3Dev Server'

# ── MySQL 数据库配置 ─────────────────────────────────────────
# 在 .env 文件中设置以下变量（数据库需提前在 MySQL 中创建）：
#   CREATE DATABASE jared3devserver CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
DB_HOST     = os.environ['DB_HOST']
DB_PORT     = int(os.environ.get('DB_PORT', 3306))
DB_USER     = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME     = os.environ['DB_NAME']

SQLALCHEMY_DATABASE_URI = (
    f'mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}'
    f'@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
)
SQLALCHEMY_ENGINE_OPTIONS      = {}
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ── 上传 Token ───────────────────────────────────────────────
# 用于 /updatehub/api/<app>/upload 等管理类接口的鉴权，
# 请求时通过 Header X-Upload-Token 或 Form/JSON 字段 token 传入。
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'data', '.token')


def load_or_create_token() -> str:
    """从文件加载上传 Token；若文件不存在则生成并保存。

    Returns:
        str: 64 位十六进制字符串 Token。
    """
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return f.read().strip()
    token = secrets.token_hex(32)
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)
    print(f"\n[{APP_NAME}] 首次运行，已生成上传 Token：{token}")
    print(f"[{APP_NAME}] Token 已保存至：{TOKEN_FILE}\n")
    return token


UPLOAD_TOKEN = load_or_create_token()

# ── Flask Session 密钥 ───────────────────────────────────────
# 用于 Flask 的 session / cookie 签名，每台服务器唯一，
# 重新生成会导致所有已登录用户的 session 失效。
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), 'data', '.secret_key')


def load_or_create_secret_key() -> str:
    """从文件加载 Flask SECRET_KEY；若文件不存在则生成并保存。

    Returns:
        str: 64 位十六进制字符串密钥。
    """
    os.makedirs(os.path.dirname(SECRET_KEY_FILE), exist_ok=True)
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, 'r') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(key)
    return key


SECRET_KEY = load_or_create_secret_key()

# ── 文件存储 ─────────────────────────────────────────────────
#: 本地上传文件根目录，结构为 uploads/<app_name>/<platform>/<filename>
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

#: 运行时数据目录（Token、密钥等持久化文件）
DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')

#: 支持的平台标识符
ALLOWED_PLATFORMS = {'windows', 'mac', 'linux'}

#: 各平台允许上传的文件扩展名白名单
ALLOWED_EXTENSIONS = {
    'windows': {'.exe', '.zip', '.msi'},
    'mac':     {'.dmg', '.pkg', '.zip'},
    'linux':   {'.tar.gz', '.deb', '.rpm', '.AppImage', '.zip'},
}

#: 单次上传文件体积上限（字节），默认 2 GB，与 Nginx client_max_body_size 保持一致
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024