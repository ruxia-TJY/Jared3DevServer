# API Stack 文档

## 概览

API Stack 是 Jared3Dev Server 内置的通用 API 托管层，提供统一的执行入口、元信息查询、
Markdown 文档展示及管理员后台。

**Base URL：** `http://<host>:5000/apistack`

---

## 访问控制

每个 API 条目拥有独立的 `visibility` 属性：

| 值        | 说明                                     |
|-----------|------------------------------------------|
| `public`  | 公开，任何人无需凭证即可调用             |
| `private` | 私有，调用时须携带有效 Token             |

### Token 传入方式（三选一）

```
Header:     X-API-Token: <token>
Query 参数: ?token=<token>
JSON body:  {"token": "<token>"}
```

Token 由管理员在后台生成，支持一个 API 绑定多个 Token，可按使用方独立吊销。

---

## 公开端点

### 执行 API

```
GET/POST /apistack/api/<api_name>
```

调用指定 API 的处理函数并返回其结果。

**路径参数**

| 参数       | 说明                                      |
|------------|-------------------------------------------|
| `api_name` | API 名称，区分大小写，须与数据库记录一致  |

**响应**

| 状态码 | 说明                                               |
|--------|----------------------------------------------------|
| 200    | 调用成功，响应体由对应处理函数决定                 |
| 401    | private API，请求中未携带 Token                    |
| 403    | private API，Token 无效；或 API 已被管理员禁用     |
| 404    | 指定名称的 API 不存在                              |
| 501    | API 已注册但处理函数尚未实现                       |
| 502    | 处理函数调用上游服务失败                           |

**示例：公开 API**

```bash
curl http://localhost:5000/apistack/api/bingWallpaper
```

```json
{
  "title": "神农架国家公园，湖北，中国",
  "copyright": "© Xinhua/Alamy",
  "url": "https://www.bing.com/th?id=OHR.ShennongjiaFog_ZH-CN...",
  "startdate": "20250308",
  "enddate": "20250309"
}
```

**示例：私有 API（Header 方式）**

```bash
curl -H "X-API-Token: your_token_here" \
     http://localhost:5000/apistack/api/myPrivateApi
```

---

### 查询 API 元信息

```
GET /apistack/info/<api_name>
```

返回指定 API 的注册信息，不含文档内容。

**响应字段**

| 字段           | 类型    | 说明                              |
|----------------|---------|-----------------------------------|
| `name`         | string  | API 标识符                        |
| `display_name` | string  | 显示名称                          |
| `description`  | string  | 一句话描述（可为 null）           |
| `author`       | string  | 作者（可为 null）                 |
| `version`      | string  | 版本号                            |
| `visibility`   | string  | `"public"` 或 `"private"`        |
| `url`          | string  | 执行端点相对路径                  |
| `enabled`      | boolean | 是否启用                          |
| `created_at`   | string  | ISO 8601 创建时间                 |
| `updated_at`   | string  | ISO 8601 最后更新时间             |

**示例**

```bash
curl http://localhost:5000/apistack/info/bingWallpaper
```

```json
{
  "name": "bingWallpaper",
  "display_name": "Bing 每日壁纸",
  "description": "获取 Bing 首页每日壁纸的标题、版权信息及原图链接",
  "author": "Jared3Dev",
  "version": "1.0.0",
  "visibility": "public",
  "url": "/apistack/api/bingWallpaper",
  "enabled": true,
  "created_at": "2025-03-09T10:00:00",
  "updated_at": "2025-03-09T10:00:00"
}
```

---

### API 文档列表

```
GET /apistack/api/doc
```

展示当前用户可见的所有 API 及其摘要信息。

- 未登录：仅显示 `visibility=public` 的 API。
- 已登录：显示全部已启用的 API。

---

### API 详细文档

```
GET /apistack/api/doc/<api_name>
```

展示指定 API 的 Markdown 使用文档（已预渲染为 HTML）。

- `public` API：任何人可查看。
- `private` API：需要登录后才能查看文档内容。

---

## 管理端点（仅管理员）

以下接口须以管理员账号登录 Web 界面后操作，或直接访问对应 URL。

| 路由                                       | 方法      | 说明               |
|--------------------------------------------|-----------|--------------------|
| `/apistack/manage/`                        | GET       | 管理列表页         |
| `/apistack/manage/add`                     | POST      | 新增 API 条目      |
| `/apistack/manage/edit/<api_id>`           | GET/POST  | 编辑 API 条目      |
| `/apistack/manage/delete/<api_id>`         | POST      | 删除 API 条目      |
| `/apistack/manage/toggle/<api_id>`         | POST      | 切换启用/禁用      |
| `/apistack/manage/doc/<api_id>`            | POST      | 更新 Markdown 文档 |
| `/apistack/manage/token/add/<api_id>`      | POST      | 生成访问 Token     |
| `/apistack/manage/token/delete/<token_id>` | POST      | 删除访问 Token     |

---

## 开发者指南：新增 API

### 第一步：在数据库注册

通过管理页面 `/apistack/manage/` 点击「新增 API」，填写：

| 字段         | 说明                                          |
|--------------|-----------------------------------------------|
| 名称         | URL slug，区分大小写，如 `bingWallpaper`      |
| 显示名称     | 人类可读名称，如 `Bing 每日壁纸`              |
| 版本         | 版本号，如 `1.0.0`                            |
| 公开性       | public（任何人）或 private（需 Token）        |
| 描述         | 可选，一句话描述                              |
| 使用文档     | 可选，Markdown 格式                           |

### 第二步：实现处理函数

在 `app/apistack/handlers.py` 末尾添加：

```python
@register('myNewApi')
def myNewApi():
    """一句话描述。

    Returns:
        Response (200): JSON 说明返回字段。
        Response (502): 上游失败时的错误响应。
    """
    # 实现业务逻辑
    return jsonify({'result': 'hello'})
```

> **注意：** `@register` 的参数须与数据库中 `ApiEntry.name` 一致（大小写不敏感）。

### 规范

- 处理函数直接返回 Flask `Response`（`jsonify` / `make_response`）。
- 外部请求失败返回 `502`，参数错误返回 `400`，业务逻辑错误返回对应状态码。
- 私有 API 的 Token 鉴权由路由层统一处理，处理函数内无需重复校验。

---

## 数据库结构

### api_entry

| 列名           | 类型         | 说明                                  |
|----------------|--------------|---------------------------------------|
| `id`           | INT PK       | 自增主键                              |
| `name`         | VARCHAR(64)  | URL slug，唯一，不可修改              |
| `display_name` | VARCHAR(128) | 显示名称                              |
| `description`  | TEXT         | 一句话描述                            |
| `author`       | VARCHAR(64)  | 作者                                  |
| `version`      | VARCHAR(32)  | 版本号                                |
| `visibility`   | VARCHAR(16)  | `public` / `private`                  |
| `enabled`      | BOOLEAN      | 是否启用                              |
| `doc_content`  | TEXT         | Markdown 文档源文件                   |
| `doc_html`     | LONGTEXT     | 预渲染 HTML（由 `doc_content` 生成）  |
| `created_at`   | DATETIME     | 创建时间                              |
| `updated_at`   | DATETIME     | 最后更新时间                          |

### api_token

| 列名         | 类型        | 说明                   |
|--------------|-------------|------------------------|
| `id`         | INT PK      | 自增主键               |
| `api_id`     | INT FK      | 关联 api_entry.id      |
| `token`      | VARCHAR(64) | 48 位十六进制字符串    |
| `label`      | VARCHAR(64) | 使用方备注             |
| `created_at` | DATETIME    | 生成时间               |