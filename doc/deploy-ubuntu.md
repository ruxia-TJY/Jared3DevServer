# Ubuntu 24 部署指南

## 架构

```
Internet → Nginx（80/443）→ Gunicorn（Unix Socket）→ Flask App → MySQL
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

# 进入 MySQL
sudo mysql

# 创建数据库和用户（替换 YOUR_PASSWORD）
CREATE DATABASE updatehub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'updatehub'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON updatehub.* TO 'updatehub'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 三、部署项目

```bash
# 克隆到服务器（或通过 scp/rsync 上传）
git clone <your-repo-url> /srv/updatehub
cd /srv/updatehub

# 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

---

## 四、配置 config.py

```bash
cp config.py config.py.bak   # 备份
nano config.py
```

修改数据库连接信息：

```python
DB_HOST     = '127.0.0.1'
DB_PORT     = 3306
DB_USER     = 'updatehub'       # 与上面创建的用户一致
DB_PASSWORD = 'YOUR_PASSWORD'   # 替换为实际密码
DB_NAME     = 'updatehub'
```

---

## 五、初始化数据库

```bash
source .venv/bin/activate
python seed.py
```

---

## 六、配置 Gunicorn（systemd 服务）

创建服务文件：

```bash
sudo nano /etc/systemd/system/updatehub.service
```

写入以下内容（注意替换路径和用户名）：

```ini
[Unit]
Description=UpdateHub Flask App
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/updatehub
Environment="PATH=/srv/updatehub/.venv/bin"
ExecStart=/srv/updatehub/.venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/run/updatehub/updatehub.sock \
    --timeout 120 \
    --access-logfile /var/log/updatehub/access.log \
    --error-logfile /var/log/updatehub/error.log \
    run:app
RuntimeDirectory=updatehub
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
```

创建日志目录并设置权限：

```bash
sudo mkdir -p /var/log/updatehub
sudo chown www-data:www-data /var/log/updatehub
sudo chown -R www-data:www-data /srv/updatehub
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now updatehub
sudo systemctl status updatehub
```

---

## 七、配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/updatehub
```

```nginx
server {
    listen 80;
    server_name your-domain.com;   # 替换为实际域名或 IP

    # 大文件上传支持（对应 MAX_CONTENT_LENGTH = 2GB）
    client_max_body_size 2G;

    # 静态文件由 Nginx 直接提供
    location /static/ {
        alias /srv/updatehub/app/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 上传文件目录（如需直接下载）
    location /uploads/ {
        alias /srv/updatehub/uploads/;
        internal;   # 禁止外部直接访问，由 Flask 控制权限
    }

    # 其余请求转发给 Gunicorn
    location / {
        proxy_pass http://unix:/run/updatehub/updatehub.sock;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

启用并重载 Nginx：

```bash
sudo ln -s /etc/nginx/sites-available/updatehub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 八、（可选）HTTPS — Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx
```

---

## 常用运维命令

| 操作 | 命令 |
|------|------|
| 查看服务状态 | `sudo systemctl status updatehub` |
| 重启服务 | `sudo systemctl restart updatehub` |
| 查看应用日志 | `sudo tail -f /var/log/updatehub/error.log` |
| 查看 Nginx 日志 | `sudo tail -f /var/log/nginx/error.log` |
| 更新代码后重启 | `git pull && sudo systemctl restart updatehub` |

---

## 开发模式（不需要 Nginx/Gunicorn）

仅用于本地调试，**不要**在生产环境使用：

```bash
source .venv/bin/activate
python run.py
```

访问 `http://<server-ip>:5000`。

> 需开放防火墙端口：`sudo ufw allow 5000`