# UpdateHub 部署与配置

## 项目结构

```
UpdateHub/
├── run.py                          # 启动入口
├── config.py                       # 全局配置（数据库、Token、文件路径等）
├── seed.py                         # 测试数据填充脚本
├── app/
│   ├── __init__.py                 # create_app() 应用工厂
│   ├── extensions.py               # 共享扩展（db、login_manager）
│   ├── updatehub/                  # 蓝图 updatehub，url_prefix='/updatehub'
│   │   ├── __init__.py
│   │   ├── models.py               # AppVersion / AppConfig / AppAccess 模型
│   │   ├── access.py               # 访问控制辅助函数
│   │   └── views.py                # 所有路由（API + HTML 页面）
│   ├── auth/                       # 蓝图 auth，url_prefix='/auth'
│   │   ├── __init__.py
│   │   └── views.py                # 登录 / 登出路由
│   ├── user/                       # 蓝图 user，url_prefix='/user'
│   │   ├── __init__.py
│   │   ├── models.py               # User 模型
│   │   └── views.py                # 用户管理路由
│   ├── utils/
│   │   ├── auth.py                 # require_token / admin_required 装饰器
│   │   ├── validators.py           # 输入校验（名称、版本、平台、扩展名）
│   │   ├── file_utils.py           # sha256_of_file
│   │   └── db_helpers.py           # get_latest_row / get_latest_dict / upsert_version
│   ├── static/
│   │   └── css/style.css           # 全局样式
│   └── templates/
│       ├── base.html               # 基础模板（导航、flash 消息）
│       ├── updatehub/
│       │   ├── index.html          # 软件列表页
│       │   ├── app_detail.html     # 软件详情页（版本列表、SHA256）
│       │   ├── _app_card.html      # 软件卡片局部模板
│       │   ├── 403.html            # 无权访问页
│       │   └── 404.html            # 软件不存在页
│       ├── auth/
│       │   └── login.html          # 登录表单
│       └── user/
│           ├── list.html           # 用户列表（管理员）
│           └── form.html           # 创建 / 编辑用户表单
├── uploads/                        # 本地上传文件（自动创建）
│   └── <app>/<platform>/
├── data/
│   ├── .token                      # 上传 Token（首次运行自动生成）
│   └── .secret_key                 # Flask Session 密钥（首次运行自动生成）
└── doc/
    ├── api.md                      # API 接口文档
    ├── setup.md                    # 本文件
    └── access.md                   # 访问控制说明
```

---

## 依赖安装

```bash
pip install flask flask-sqlalchemy flask-login pymysql werkzeug packaging requests
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
> 启动后表结构会自动创建（`db.create_all()`）。

### 文件存储

```python
UPLOAD_FOLDER      = './uploads'                  # 本地上传文件根目录
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024      # 单文件最大 2 GB
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

### app_version — 软件版本信息

唯一约束：`(app_name, version, platform)`

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

### app_config — 软件访问控制配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `app_name` | VARCHAR(64) | 主键，软件名称 |
| `access_level` | VARCHAR(16) | `public` / `protected` / `restricted`，默认 `public` |

### app_access — 受限软件授权用户

唯一约束：`(app_name, user_id)`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT | 主键，自增 |
| `app_name` | VARCHAR(64) | 软件名称 |
| `user_id` | INT | 外键 → `user.id`，级联删除 |

### user — 系统用户

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT | 主键，自增 |
| `username` | VARCHAR(64) | 唯一用户名 |
| `email` | VARCHAR(128) | 可选邮箱，唯一 |
| `password_hash` | VARCHAR(256) | Werkzeug bcrypt 哈希 |
| `role` | VARCHAR(16) | `admin` / `user`，默认 `user` |
| `active` | BOOLEAN | 账号是否启用，默认 `true` |
| `created_at` | DATETIME | 创建时间 |

---

## 启动

```bash
python run.py
```

服务默认监听 `0.0.0.0:5000`，启动时自动完成：

1. 连接 MySQL 并创建所有数据表（如不存在）
2. 注册三个蓝图：`updatehub`（`/updatehub`）、`auth`（`/auth`）、`user`（`/user`）
3. 加载或生成上传 Token 与 Session 密钥

---

## 填充测试数据

```bash
python seed.py
```

默认创建 4 个用户和 3 款测试软件：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| alice | alice123 | 普通用户 |
| bob | bob123 | 普通用户 |
| charlie | charlie123 | 普通用户 |

| 软件 | 访问级别 | 说明 |
|------|----------|------|
| MyEditor | public | 所有人可访问 |
| DataSync | protected | 需登录 |
| QuickNote | restricted | 仅 admin 和 alice |

---

## 三种文件来源对比

| 来源 | 注册接口 | 下载行为 | 适用场景 |
|------|---------|---------|---------|
| `local` | `POST /updatehub/api/<app>/upload`（multipart） | 服务器直接返回文件 | 文件较小或需要完全自托管 |
| `github` | `POST /updatehub/api/<app>/register`（JSON） | 302 重定向至 GitHub | 希望节省服务器流量 |
| `github_proxy` | `POST /updatehub/api/<app>/register`（JSON） | 服务器中转流式传输 | 隐藏 GitHub 源地址或国内加速 |

---

## Web 界面路由

| 路径 | 说明 |
|------|------|
| `GET /updatehub/` | 软件列表页，按访问级别分组显示 |
| `GET /updatehub/<app>` | 软件详情页，显示所有版本及 SHA256 |
| `GET /auth/login` | 登录页 |
| `GET /auth/logout` | 登出 |
| `GET /user/` | 用户列表（仅管理员） |
| `GET/POST /user/create` | 创建用户（仅管理员） |
| `GET/POST /user/<id>/edit` | 编辑用户 |
| `POST /user/<id>/delete` | 删除用户（仅管理员） |
| `GET /user/profile` | 跳转到当前用户编辑页 |
