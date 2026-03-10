# Jared3Dev Server · Ubuntu 24 部署指南

## 架构总览

```
Internet
  │
  ▼
Nginx（80 / 443）          ← 反向代理、静态文件直出、HTTPS 终止
  │
  ▼ Unix Socket
Gunicorn（4 Workers）      ← WSGI 进程管理，由 systemd 守护
  │
  ▼
Flask App                  ← Jared3Dev Server 应用本体
  │
  ▼
MySQL 8                    ← 数据持久化（jared3devserver 库）
```

---

## 一、系统准备

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx mysql-server
```

---

## 二、MySQL 配置

```bash
# 启动并设置开机自启
sudo systemctl enable --now mysql

# 安全初始化（设置 root 密码等）
sudo mysql_secure_installation

# 进入 MySQL
sudo mysql
```

```sql
-- 创建数据库
CREATE DATABASE jared3devserver
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 创建专用用户（替换 YOUR_PASSWORD）
CREATE USER 'jared3dev'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON jared3devserver.* TO 'jared3dev'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 三、部署项目

```bash
# 克隆代码（或通过 scp / rsync 上传）
git clone <your-repo-url> /srv/jared3devserver
cd /srv/jared3devserver

# 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

---

## 四、配置 config.py

```bash
nano /srv/jared3devserver/config.py
```

修改数据库连接信息：

```python
DB_HOST     = '127.0.0.1'
DB_PORT     = 3306
DB_USER     = 'jared3dev'        # 与上面创建的 MySQL 用户一致
DB_PASSWORD = 'YOUR_PASSWORD'    # 替换为实际密码
DB_NAME     = 'jared3devserver'
```

> `config.py` 已加入 `.gitignore`，密码不会提交到版本库。

---

## 五、初始化数据库

```bash
cd /srv/jared3devserver
source .venv/bin/activate

# 建表 + 写入测试数据
python seed.py
```

首次运行会自动：
- 创建所有数据表（`db.create_all()`）
- 生成上传 Token（保存至 `data/.token`）
- 生成 Flask Session 密钥（保存至 `data/.secret_key`）

---

## 六、设置目录权限

```bash
# 创建日志目录
sudo mkdir -p /var/log/jared3devserver

# 将项目目录和日志目录归属给 www-data
sudo chown -R www-data:www-data /srv/jared3devserver
sudo chown    www-data:www-data /var/log/jared3devserver
```

---

## 七、配置 Gunicorn（systemd 服务）

```bash
sudo nano /etc/systemd/system/jared3devserver.service
```

```ini
[Unit]
Description=Jared3Dev Server
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/jared3devserver
Environment="PATH=/srv/jared3devserver/.venv/bin"
ExecStart=/srv/jared3devserver/.venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/run/jared3devserver/jared3devserver.sock \
    --timeout 120 \
    --access-logfile /var/log/jared3devserver/access.log \
    --error-logfile  /var/log/jared3devserver/error.log \
    run:app
RuntimeDirectory=jared3devserver
RuntimeDirectoryMode=0755
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now jared3devserver
sudo systemctl status jared3devserver
```

---

## 八、配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/jared3devserver
```

```nginx
server {
    listen 80;
    server_name your-domain.com;   # 替换为实际域名或服务器 IP

    # 单文件上传上限与 MAX_CONTENT_LENGTH 一致
    client_max_body_size 2G;

    # 静态资源由 Nginx 直接提供，不经过 Python
    # expires 7d 与应用层 Cache Busting（?v=时间戳）配合使用：
    # 文件不变时浏览器直接使用缓存；文件更新后 URL 的 ?v= 变化，浏览器自动拉取新版本
    location /static/ {
        alias /srv/jared3devserver/app/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 本地上传文件目录（internal 禁止外部直接访问，Flask 通过 X-Accel-Redirect 控制）
    location /uploads/ {
        alias /srv/jared3devserver/uploads/;
        internal;
    }

    # 其余请求转发给 Gunicorn
    location / {
        proxy_pass         http://unix:/run/jared3devserver/jared3devserver.sock;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/jared3devserver \
           /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 九、（可选）HTTPS — Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
# certbot 会自动修改 Nginx 配置并重载
```

证书自动续期已由 certbot 的 systemd timer 处理，无需额外配置。

---

## 十、验证部署

```bash
# 服务状态
sudo systemctl status jared3devserver

# 实时应用日志
sudo tail -f /var/log/jared3devserver/error.log

# 实时访问日志
sudo tail -f /var/log/jared3devserver/access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 测试接口（替换域名）
curl http://your-domain.com/apistack/info/bingWallpaper
```

---

## 常用运维命令

| 操作 | 命令 |
|------|------|
| 查看服务状态 | `sudo systemctl status jared3devserver` |
| 重启服务 | `sudo systemctl restart jared3devserver` |
| 停止服务 | `sudo systemctl stop jared3devserver` |
| 查看应用日志 | `sudo tail -f /var/log/jared3devserver/error.log` |
| 更新代码 | `git pull && sudo systemctl restart jared3devserver` |
| 重载 Nginx | `sudo systemctl reload nginx` |

---

## 开发模式（仅本地调试）

> **不要**在生产环境使用以下方式，Flask 内置服务器不适合生产负载。

```bash
cd /srv/jared3devserver
source .venv/bin/activate
python run.py
# 访问 http://<server-ip>:5000
```

开放防火墙端口（如需远程访问）：

```bash
sudo ufw allow 5000
```