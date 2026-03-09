# UpdateHub API 文档

## 概览

UpdateHub 用于管理多个软件、多个平台的版本发布与下载。支持三种文件来源：

| 来源 | 说明 |
|------|------|
| `local` | 文件存储在服务器本地，直接下载 |
| `github` | 文件托管在 GitHub Release，服务器返回 302 重定向，客户端直连 GitHub 下载 |
| `github_proxy` | 文件托管在 GitHub Release，服务器作为中转站从 GitHub 拉取后流式传给客户端 |

**Base URL：** `http://<host>:5000/updatehub`

**支持平台：** `windows` / `mac` / `linux`

---

## 认证

### API Token（管理类接口）

需要 Token 的接口通过以下任一方式传入：

- **HTTP Header：** `X-Upload-Token: <token>`
- **Form 字段：** `token=<token>`
- **JSON 字段：** `{ "token": "<token>" }`

Token 首次启动时自动生成，保存于 `data/.token`。

### 访问控制（查询/下载类接口）

软件支持三种访问级别，不同级别对未认证用户的行为不同：

| 访问级别 | 说明 | API 未认证时返回 |
|----------|------|-----------------|
| `public` | 无需登录 | 正常返回数据 |
| `protected` | 需要登录（任意已认证用户） | `401` |
| `restricted` | 仅指定用户及管理员 | `401` / `403` |

Web 页面通过 Session Cookie 认证（`POST /auth/login`）；
API 客户端若需访问受保护软件，须先通过登录接口获取 Session Cookie，或联系管理员将该软件设为 `public`。

---

## 接口列表

### 1. 列出所有软件

```
GET /updatehub/api/apps
```

**说明：** 列出所有已注册软件及各平台最新版本，**不过滤**访问级别（客户端自行判断）。

**响应示例**

```json
{
  "apps": [
    {
      "app": "MyEditor",
      "latest": {
        "windows": "2.1.0",
        "linux": "2.0.0"
      },
      "version_count": 5
    }
  ]
}
```

---

### 2. 获取最新版本

```
GET /updatehub/api/<app>/latest
GET /updatehub/api/<app>/latest?platform=windows
```

**Query 参数**

| 参数 | 必填 | 说明 |
|------|------|------|
| `platform` | 否 | `windows` / `mac` / `linux`，不传则返回所有平台 |

**响应示例（指定平台）**

```json
{
  "app": "MyEditor",
  "platform": "windows",
  "version": "2.1.0",
  "source": "github_proxy",
  "release_notes": "修复若干问题",
  "release_date": "2026-03-08",
  "file_size": 12345678,
  "sha256": "abc123...",
  "mandatory": false,
  "download_url": "/updatehub/api/MyEditor/download?platform=windows&version=2.1.0"
}
```

**响应示例（所有平台）**

```json
{
  "app": "MyEditor",
  "latest": {
    "windows": {
      "version": "2.1.0",
      "source": "github_proxy",
      "release_notes": "修复若干问题",
      "release_date": "2026-03-08",
      "file_size": 12345678,
      "sha256": "abc123...",
      "mandatory": false,
      "download_url": "/updatehub/api/MyEditor/download?platform=windows&version=2.1.0"
    }
  }
}
```

---

### 3. 检查更新

```
GET /updatehub/api/<app>/check?platform=windows&version=1.0.0
```

**Query 参数**

| 参数 | 必填 | 说明 |
|------|------|------|
| `platform` | 是 | `windows` / `mac` / `linux` |
| `version` | 是 | 客户端当前版本号，如 `1.0.0` |

**响应示例（有更新）**

```json
{
  "has_update": true,
  "latest_version": "2.1.0",
  "mandatory": false,
  "release_notes": "修复若干问题",
  "release_date": "2026-03-08",
  "file_size": 12345678,
  "sha256": "abc123...",
  "download_url": "/updatehub/api/MyEditor/download?platform=windows&version=2.1.0"
}
```

**响应示例（无更新）**

```json
{
  "has_update": false,
  "latest_version": "2.1.0"
}
```

---

### 4. 下载文件

```
GET /updatehub/api/<app>/download?platform=windows&version=2.1.0
```

**Query 参数**

| 参数 | 必填 | 说明 |
|------|------|------|
| `platform` | 是 | `windows` / `mac` / `linux` |
| `version` | 是 | 要下载的版本号 |

**行为说明**

| 版本来源 | 行为 |
|----------|------|
| `local` | 直接返回文件（`200 + 文件流`） |
| `github` | 返回 `302` 重定向到 GitHub Release 原始地址 |
| `github_proxy` | 服务器从 GitHub 拉取后流式中转，客户端无需感知来源 |

---

### 5. 列出所有版本

```
GET /updatehub/api/<app>/versions
```

**响应示例**

```json
{
  "app": "MyEditor",
  "latest": {
    "windows": "2.1.0"
  },
  "versions": {
    "2.1.0": {
      "windows": {
        "source": "github_proxy",
        "github_url": "https://github.com/user/repo/releases/download/v2.1.0/app.exe",
        "file_size": 12345678,
        "sha256": "abc123...",
        "release_notes": "修复若干问题",
        "release_date": "2026-03-08",
        "mandatory": false
      }
    },
    "2.0.0": {
      "windows": {
        "source": "local",
        "filename": "MyEditor-2.0.0-windows.exe",
        "file_size": 11000000,
        "sha256": "def456...",
        "release_notes": "初始版本",
        "release_date": "2026-01-01",
        "mandatory": false
      }
    }
  }
}
```

---

### 6. 上传本地文件版本

```
POST /updatehub/api/<app>/upload
```

**认证：** 需要 Token

**Content-Type：** `multipart/form-data`

**Form 参数**

| 字段 | 必填 | 说明 |
|------|------|------|
| `platform` | 是 | `windows` / `mac` / `linux` |
| `version` | 是 | 版本号，如 `1.0.1` |
| `file` | 是 | 安装包文件 |
| `release_notes` | 否 | 更新说明 |
| `mandatory` | 否 | 是否强制更新，`true` / `false`，默认 `false` |

**允许的文件格式**

| 平台 | 格式 |
|------|------|
| windows | `.exe` `.zip` `.msi` |
| mac | `.dmg` `.pkg` `.zip` |
| linux | `.tar.gz` `.deb` `.rpm` `.AppImage` `.zip` |

**curl 示例**

```bash
curl -X POST http://localhost:5000/updatehub/api/MyEditor/upload \
  -H "X-Upload-Token: <token>" \
  -F "platform=windows" \
  -F "version=2.1.0" \
  -F "release_notes=修复若干问题" \
  -F "mandatory=false" \
  -F "file=@MyEditor-2.1.0.exe"
```

**响应示例**

```json
{
  "success": true,
  "app": "MyEditor",
  "version": "2.1.0",
  "platform": "windows",
  "filename": "MyEditor-2.1.0-windows.exe",
  "file_size": 12345678,
  "sha256": "abc123..."
}
```

---

### 7. 注册 GitHub Release 版本

```
POST /updatehub/api/<app>/register
```

**认证：** 需要 Token

**Content-Type：** `application/json`

**JSON 参数**

| 字段 | 必填 | 说明 |
|------|------|------|
| `platform` | 是 | `windows` / `mac` / `linux` |
| `version` | 是 | 版本号，如 `2.1.0` |
| `github_url` | 是 | GitHub Release 文件直链，必须以 `https://github.com/` 开头 |
| `source` | 否 | `github`（重定向）或 `github_proxy`（中转代理），默认 `github_proxy` |
| `release_notes` | 否 | 更新说明 |
| `mandatory` | 否 | 是否强制更新，默认 `false` |
| `file_size` | 否 | 文件大小（字节），用于客户端显示进度 |
| `sha256` | 否 | 文件 SHA256 校验值 |

**curl 示例**

```bash
# 中转代理（推荐，隐藏 GitHub 源地址）
curl -X POST http://localhost:5000/updatehub/api/MyEditor/register \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "windows",
    "version": "2.1.0",
    "github_url": "https://github.com/user/repo/releases/download/v2.1.0/app.exe",
    "source": "github_proxy",
    "release_notes": "修复若干问题",
    "mandatory": false
  }'

# 直接重定向（客户端直连 GitHub）
curl -X POST http://localhost:5000/updatehub/api/MyEditor/register \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "linux",
    "version": "2.1.0",
    "github_url": "https://github.com/user/repo/releases/download/v2.1.0/app.tar.gz",
    "source": "github"
  }'
```

**响应示例**

```json
{
  "success": true,
  "app": "MyEditor",
  "version": "2.1.0",
  "platform": "windows",
  "source": "github_proxy",
  "github_url": "https://github.com/user/repo/releases/download/v2.1.0/app.exe"
}
```

---

### 8. 删除版本

```
DELETE /updatehub/api/<app>/delete?platform=windows&version=2.0.0
```

**认证：** 需要 Token

**Query 参数**

| 参数 | 必填 | 说明 |
|------|------|------|
| `platform` | 是 | `windows` / `mac` / `linux` |
| `version` | 是 | 要删除的版本号 |

- `local` 来源：同时删除服务器上的安装包文件
- `github` / `github_proxy` 来源：仅删除数据库记录，不影响 GitHub 上的文件

**curl 示例**

```bash
curl -X DELETE \
  "http://localhost:5000/updatehub/api/MyEditor/delete?platform=windows&version=2.0.0" \
  -H "X-Upload-Token: <token>"
```

**响应示例**

```json
{
  "success": true,
  "message": "MyEditor v2.0.0 (windows) 已删除"
}
```

---

### 9. 查询访问控制配置

```
GET /updatehub/api/<app>/access
```

**认证：** 需要 Token

**响应示例（public）**

```json
{
  "app": "MyEditor",
  "access_level": "public",
  "users": []
}
```

**响应示例（restricted）**

```json
{
  "app": "QuickNote",
  "access_level": "restricted",
  "users": [
    { "user_id": 2, "username": "alice" }
  ]
}
```

---

### 10. 修改访问级别

```
POST /updatehub/api/<app>/access
```

**认证：** 需要 Token

**Content-Type：** `application/json`

**JSON 参数**

| 字段 | 必填 | 说明 |
|------|------|------|
| `access_level` | 是 | `public` / `protected` / `restricted` |

**curl 示例**

```bash
curl -X POST http://localhost:5000/updatehub/api/QuickNote/access \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"access_level": "restricted"}'
```

**响应示例**

```json
{
  "success": true,
  "app": "QuickNote",
  "access_level": "restricted"
}
```

---

### 11. 授权用户访问受限软件

```
POST /updatehub/api/<app>/access/users
```

**认证：** 需要 Token

**Content-Type：** `application/json`

**JSON 参数**（二选一）

| 字段 | 说明 |
|------|------|
| `username` | 通过用户名指定用户 |
| `user_id` | 通过用户 ID 指定用户 |

**curl 示例**

```bash
curl -X POST http://localhost:5000/updatehub/api/QuickNote/access/users \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice"}'
```

**响应示例**

```json
{
  "success": true,
  "app": "QuickNote",
  "username": "alice"
}
```

---

### 12. 撤销用户访问权限

```
DELETE /updatehub/api/<app>/access/users/<user_id>
```

**认证：** 需要 Token

**curl 示例**

```bash
curl -X DELETE \
  http://localhost:5000/updatehub/api/QuickNote/access/users/2 \
  -H "X-Upload-Token: <token>"
```

**响应示例**

```json
{
  "success": true,
  "app": "QuickNote",
  "user_id": 2
}
```

---

## 错误码

| HTTP 状态码 | 场景 |
|-------------|------|
| `400` | 请求参数错误（平台非法、版本号格式错误、文件类型不支持等） |
| `401` | Token 无效 / 未提供；或访问受保护软件时未登录 |
| `403` | 已登录但无权访问该受限软件 |
| `404` | 软件或版本不存在；用户不存在 |
| `502` | 中转下载时 GitHub 返回错误 |

---

## 文件存储结构

```
uploads/
└── <app>/
    ├── windows/
    │   └── <app>-<version>-windows.exe
    ├── mac/
    │   └── <app>-<version>-mac.dmg
    └── linux/
        └── <app>-<version>-linux.tar.gz

data/
├── .token       # 上传 Token（请勿泄露）
└── .secret_key  # Flask Session 密钥（请勿泄露）
```
