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

需要认证的接口通过以下任一方式传入 Token：

- **HTTP Header：** `X-Upload-Token: <token>`
- **Form 字段：** `token=<token>`
- **JSON 字段：** `{ "token": "<token>" }`

Token 首次启动时自动生成，保存于 `data/.token`。

---

## 接口列表

### 1. 列出所有软件

```
GET /updatehub/api/apps
```

**响应示例**

```json
{
  "apps": [
    {
      "app": "my_app",
      "latest": {
        "windows": "1.0.1",
        "linux": "1.0.0"
      },
      "version_count": 2
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
  "app": "my_app",
  "platform": "windows",
  "version": "1.0.1",
  "source": "github_proxy",
  "release_notes": "修复若干问题",
  "release_date": "2026-03-08",
  "file_size": 12345678,
  "sha256": "abc123...",
  "mandatory": false,
  "download_url": "/updatehub/api/my_app/download?platform=windows&version=1.0.1"
}
```

**响应示例（所有平台）**

```json
{
  "app": "my_app",
  "latest": {
    "windows": {
      "version": "1.0.1",
      "source": "github_proxy",
      "release_notes": "修复若干问题",
      "release_date": "2026-03-08",
      "file_size": 12345678,
      "sha256": "abc123...",
      "mandatory": false,
      "download_url": "/updatehub/api/my_app/download?platform=windows&version=1.0.1"
    },
    "linux": { "..." : "..." }
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
  "latest_version": "1.0.1",
  "mandatory": false,
  "release_notes": "修复若干问题",
  "release_date": "2026-03-08",
  "file_size": 12345678,
  "sha256": "abc123...",
  "download_url": "/updatehub/api/my_app/download?platform=windows&version=1.0.1"
}
```

**响应示例（无更新）**

```json
{
  "has_update": false,
  "latest_version": "1.0.1"
}
```

---

### 4. 下载文件

```
GET /updatehub/api/<app>/download?platform=windows&version=1.0.1
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
  "app": "my_app",
  "latest": {
    "windows": "1.0.1"
  },
  "versions": {
    "1.0.1": {
      "windows": {
        "source": "github_proxy",
        "github_url": "https://github.com/user/repo/releases/download/v1.0.1/app.exe",
        "file_size": 12345678,
        "sha256": "abc123...",
        "release_notes": "修复若干问题",
        "release_date": "2026-03-08",
        "mandatory": false
      }
    },
    "1.0.0": {
      "windows": {
        "source": "local",
        "filename": "my_app-1.0.0-windows.exe",
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
curl -X POST http://localhost:5000/updatehub/api/my_app/upload \
  -H "X-Upload-Token: <token>" \
  -F "platform=windows" \
  -F "version=1.0.1" \
  -F "release_notes=修复若干问题" \
  -F "mandatory=false" \
  -F "file=@my_app-1.0.1.exe"
```

**响应示例**

```json
{
  "success": true,
  "app": "my_app",
  "version": "1.0.1",
  "platform": "windows",
  "filename": "my_app-1.0.1-windows.exe",
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
| `version` | 是 | 版本号，如 `1.0.1` |
| `github_url` | 是 | GitHub Release 文件直链，必须以 `https://github.com/` 开头 |
| `source` | 否 | `github`（重定向）或 `github_proxy`（中转代理），默认 `github_proxy` |
| `release_notes` | 否 | 更新说明 |
| `mandatory` | 否 | 是否强制更新，默认 `false` |
| `file_size` | 否 | 文件大小（字节），用于客户端显示进度 |
| `sha256` | 否 | 文件 SHA256 校验值 |

**curl 示例**

```bash
# 中转代理（推荐，隐藏 GitHub 源地址）
curl -X POST http://localhost:5000/updatehub/api/my_app/register \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "windows",
    "version": "1.0.1",
    "github_url": "https://github.com/user/repo/releases/download/v1.0.1/app.exe",
    "source": "github_proxy",
    "release_notes": "修复若干问题",
    "mandatory": false
  }'

# 直接重定向（客户端直连 GitHub）
curl -X POST http://localhost:5000/updatehub/api/my_app/register \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "linux",
    "version": "1.0.1",
    "github_url": "https://github.com/user/repo/releases/download/v1.0.1/app.tar.gz",
    "source": "github"
  }'
```

**响应示例**

```json
{
  "success": true,
  "app": "my_app",
  "version": "1.0.1",
  "platform": "windows",
  "source": "github_proxy",
  "github_url": "https://github.com/user/repo/releases/download/v1.0.1/app.exe"
}
```

---

### 8. 删除版本

```
DELETE /updatehub/api/<app>/delete?platform=windows&version=1.0.0
```

**认证：** 需要 Token（放在 Header 中）

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
  "http://localhost:5000/updatehub/api/my_app/delete?platform=windows&version=1.0.0" \
  -H "X-Upload-Token: <token>"
```

**响应示例**

```json
{
  "success": true,
  "message": "my_app v1.0.0 (windows) 已删除"
}
```

---

## 错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| `400` | 请求参数错误（平台非法、版本号格式错误、文件类型不支持等） |
| `401` | Token 无效或未提供 |
| `404` | 软件或版本不存在 |
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
└── .token      # 上传 Token（请勿泄露）
```