"""
run.py - 应用启动入口。

直接运行此文件以在开发/生产环境中启动 UpdateHub 服务：
    python run.py

启动时会自动创建 uploads/ 和 data/ 目录（若不存在）。
服务监听 0.0.0.0:5000，生产环境建议在前端配置反向代理。
"""
import os
import config
from app import create_app

app = create_app()

if __name__ == '__main__':
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.DATA_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
