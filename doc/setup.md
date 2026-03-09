# UpdateHub 部署与配置

## 项目结构

```
UpdateHub/
├── run.py                      # 启动入口
├── config.py                   # 全局配置（数据库、Token、文件路径等）
├── app/
│   ├── __init__.py             # create_app() 工厂函数
│   ├── extensions.py           # SQLAlchemy 实例
│   ├── models/
│   │   ├── __init__.py
│   │   └── version.py          # AppVersion 数据库模型
│   ├── updatehub/              # Blueprint 'updatehub'，url_prefix='/updatehub'
│   │   ├── __init__.py
│   │   ├── apps.py             # GET  /updatehub/api/apps
│   │   ├── versions.py         # GET  /updatehub/api/<app>/latest|versions|check
│   │   ├── download.py         # GET  /updatehub/api/<app>/download
│   │   └── manage.py           # POST /updatehub/api/<app>/upload|register
│   │                           # DEL  /updatehub/api/<app>/delete
│   └── utils/
│       ├── auth.py             # require_token 认证装饰器
│       ├── validators.py       # 参数校验（app名、版本号、平台、文件扩展名）
│       ├── file_utils.py       # sha256_of_file
│       └── db_helpers.py       # get_latest_row / get_latest_dict / upsert_version
├── uploads/                    # 本地上传文件存储目录（自动创建）
│   └── <app>/
│       ├── windows/
│       ├── mac/
│       └── linux/
├── data/
│   └── .token                  # 上传 Token（首次运行自动生成）
└── doc/
    ├── api.md                  # API 接口文档
    └── setup.md                # 本文件
```

---

## 依赖安装

```bash
pip install flask flask-sqlalchemy pymysql packaging requests
```

---

## 配置说明

所有配置集中在 `config.py`，按需修改后启动即可。

### 数据库配置

```python
DB_HOST     = '127.0.0.1'    # MySQL 主机
DB_PORT     = 3306            # MySQL 端口
DB_USER     = 'root'          # 用户名
DB_PASSWORD = 'your_password' # 密码
DB_NAME     = 'updatehub'     # 数据库名
```

> 首次使用前需在 MySQL 中手动创建数据库：
> ```sql
> CREATE DATABASE updatehub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> ```
> 启动后表结构会自动创建。

### 文件存储

```python
UPLOAD_FOLDER = './uploads'                        # 本地上传文件根目录
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024       # 单文件最大 2 GB
```

### 允许的文件格式

```python
ALLOWED_EXTENSIONS = {
    'windows': {'.exe', '.zip', '.msi'},
    'mac':     {'.dmg', '.pkg', '.zip'},
    'linux':   {'.tar.gz', '.deb', '.rpm', '.AppImage', '.zip'},
}
```

### 上传 Token

首次运行自动生成，保存在 `data/.token`，控制台也会打印一次：

```
[UpdateHub] 首次运行，已生成上传 Token：1c833f57d574...
[UpdateHub] Token 已保存至：D:\...\data\.token
```

---

## 数据库表结构

表名：`app_version`，唯一约束：`(app_name, version, platform)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT | 主键，自增 |
| `app_name` | VARCHAR(64) | 软件名称 |
| `version` | VARCHAR(32) | 版本号（遵循 PEP 440） |
| `platform` | VARCHAR(16) | `windows` / `mac` / `linux` |
| `source` | VARCHAR(16) | `local` / `github` / `github_proxy` |
| `filename` | VARCHAR(256) | 本地文件名（仅 `local`） |
| `github_url` | VARCHAR(512) | GitHub 文件直链（仅 `github` / `github_proxy`） |
| `file_size` | BIGINT | 文件大小（字节） |
| `sha256` | VARCHAR(64) | SHA256 校验值 |
| `release_notes` | TEXT | 更新说明 |
| `release_date` | DATE | 发布日期 |
| `mandatory` | BOOLEAN | 是否强制更新 |
| `created_at` | DATETIME | 记录创建时间 |

---

## 启动

```bash
python run.py
```

服务默认监听 `0.0.0.0:5000`，启动时自动完成：
1. 连接 MySQL 并创建 `app_version` 表（如不存在）
2. 注册 Blueprint `updatehub`（url_prefix `/updatehub`）
3. 加载或生成上传 Token

---

## 三种文件来源对比

| 来源 | 注册接口 | 下载行为 | 适用场景 |
|------|---------|---------|---------|
| `local` | `POST /updatehub/api/<app>/upload`（multipart） | 服务器直接返回文件 | 文件较小或需要完全自托管 |
| `github` | `POST /updatehub/api/<app>/register`（JSON） | 302 重定向至 GitHub | 希望节省服务器流量 |
| `github_proxy` | `POST /updatehub/api/<app>/register`（JSON） | 服务器中转流式传输 | 隐藏 GitHub 源地址或国内加速 |