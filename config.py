import os
import secrets
from urllib.parse import quote_plus

# ──────────────────────────────────────────────
# 项目名称
# ──────────────────────────────────────────────
APP_NAME = 'UpdateHub'

# ──────────────────────────────────────────────
# MySQL 数据库配置
# ──────────────────────────────────────────────
DB_HOST     = '127.0.0.1'
DB_PORT     = 3306
DB_USER     = 'root'
DB_PASSWORD = 'YOUR_PASSWORD'
DB_NAME     = 'updatehub'

SQLALCHEMY_DATABASE_URI = (
    f'mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}'
    f'@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
)
SQLALCHEMY_ENGINE_OPTIONS = {}

SQLALCHEMY_TRACK_MODIFICATIONS = False

# ──────────────────────────────────────────────
# 上传 Token（首次运行自动生成并保存）
# ──────────────────────────────────────────────
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'data', '.token')

def load_or_create_token():
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

# ──────────────────────────────────────────────
# Flask Session 密钥（首次运行自动生成并保存）
# ──────────────────────────────────────────────
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), 'data', '.secret_key')

def load_or_create_secret_key():
    os.makedirs(os.path.dirname(SECRET_KEY_FILE), exist_ok=True)
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, 'r') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(key)
    return key

SECRET_KEY = load_or_create_secret_key()

# ──────────────────────────────────────────────
# 文件存储
# ──────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DATA_FOLDER   = os.path.join(os.path.dirname(__file__), 'data')

ALLOWED_PLATFORMS = {'windows', 'mac', 'linux'}

# 各平台允许上传的文件扩展名
ALLOWED_EXTENSIONS = {
    'windows': {'.exe', '.zip', '.msi'},
    'mac':     {'.dmg', '.pkg', '.zip'},
    'linux':   {'.tar.gz', '.deb', '.rpm', '.AppImage', '.zip'},
}

MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2 GB