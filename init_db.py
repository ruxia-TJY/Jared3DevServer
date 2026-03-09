"""
init_db.py - 创建数据库及表结构，不写入任何数据。

运行方式：
  python init_db.py
  或通过 FLASK_APP=init_db.py flask run（仅用于初始化，不启动服务）

执行内容：
  1. 自动生成 data/.token 和 data/.secret_key（首次运行）
  2. 创建 MySQL 数据库（若不存在）
  3. 创建所有数据表（db.create_all()）
"""
import pymysql
import config
from app import create_app as _create_app


def _create_database():
    conn = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset='utf8mb4',
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        print(f'[init_db] 数据库 `{config.DB_NAME}` 已就绪。')
    finally:
        conn.close()


def create_app():
    """供 Flask CLI 识别的工厂函数，先建库再建表。"""
    _create_database()
    app = _create_app()
    print('[init_db] 数据库表结构初始化完成。')
    return app


if __name__ == '__main__':
    create_app()