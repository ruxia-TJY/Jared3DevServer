# UpdateHub 访问控制说明

## 访问级别

每款软件可独立设置访问级别，共三种：

| 级别 | 常量 | 说明 |
|------|------|------|
| `public` | `ACCESS_PUBLIC` | 无需登录，任何人（含匿名访问者）均可查看和下载 |
| `protected` | `ACCESS_PROTECTED` | 需要登录，任意已认证用户均可访问 |
| `restricted` | `ACCESS_RESTRICTED` | 仅**管理员**及被**单独授权**的用户可访问 |

未在数据库中配置的软件默认按 `public` 处理。

---

## 访问判断逻辑

```
                    ┌─ public ──────────────────────────────── 允许
访问请求 ─── 获取级别 ┤
                    ├─ protected ─── 已登录? ─── 是 ──────── 允许
                    │                        └─ 否 ──────── 拒绝(401)
                    │
                    └─ restricted ── 已登录? ─── 否 ──────── 拒绝(401)
                                             └─ 是 ─ 是管理员? ─── 是 ── 允许
                                                            └─ 否 ─ 在授权名单? ─ 是 ── 允许
                                                                                  └─ 否 ── 拒绝(403)
```

---

## 行为差异

### Web 页面

| 场景 | 行为 |
|------|------|
| 无权（未登录） | 重定向到登录页，登录后自动跳回原页面 |
| 无权（已登录） | 渲染 `403.html` 页面 |
| 首页列表 | 仅展示当前用户**有权访问**的软件，其余不显示 |

### API 接口

| 场景 | HTTP 状态码 | 响应体 |
|------|------------|--------|
| 无权（未登录） | `401` | `{"error": "请先登录后访问此软件"}` |
| 无权（已登录） | `403` | `{"error": "您没有访问此软件的权限"}` |

---

## 管理操作

访问控制配置通过 Token 认证的 API 管理，**不需要**通过 Web 登录。

### 查看当前配置

```bash
curl http://localhost:5000/updatehub/api/QuickNote/access \
  -H "X-Upload-Token: <token>"
```

### 设置访问级别

```bash
# 设为受限（仅指定用户）
curl -X POST http://localhost:5000/updatehub/api/QuickNote/access \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"access_level": "restricted"}'

# 设为需登录
curl -X POST http://localhost:5000/updatehub/api/DataSync/access \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"access_level": "protected"}'

# 设为公开
curl -X POST http://localhost:5000/updatehub/api/MyEditor/access \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"access_level": "public"}'
```

### 授权用户（restricted 级别）

```bash
# 通过用户名授权
curl -X POST http://localhost:5000/updatehub/api/QuickNote/access/users \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice"}'

# 通过用户 ID 授权
curl -X POST http://localhost:5000/updatehub/api/QuickNote/access/users \
  -H "X-Upload-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2}'
```

### 撤销授权

```bash
curl -X DELETE \
  http://localhost:5000/updatehub/api/QuickNote/access/users/2 \
  -H "X-Upload-Token: <token>"
```

---

## 注意事项

- **管理员始终有权**访问所有级别的软件，无需单独授权。
- 删除用户时，该用户在 `app_access` 表中的所有授权记录会**级联删除**。
- 将软件从 `restricted` 改为 `public` 或 `protected` 后，原有的授权记录仍保留在数据库，
  若再次改回 `restricted`，之前授权的用户依然有效。
- `app_config` 表无记录的软件等同于 `public`，不影响正常使用；
  若需明确标记为 `public`，可调用设置接口写入记录。
