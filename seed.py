"""
seed.py - 向数据库插入示例数据，用于开发测试。
运行方式：python seed.py

生成内容：
  用户  : 1 名管理员 + 3 名普通用户
  软件  : MyEditor / DataSync / QuickNote（各含多个版本和平台）
  访问控制:
    MyEditor  -> public     （无需登录）
    DataSync  -> protected  （需要登录）
    QuickNote -> restricted （仅 alice + 管理员）
"""
import os
from datetime import date

from app import create_app
from app.extensions import db
from app.updatehub.models import AppVersion, AppConfig, AppAccess
from app.user.models import User

# ── 用户数据 ────────────────────────────────────────────────

USERS = [
    dict(username='admin',   password='admin123',   email='admin@example.com',   role='admin', active=True),
    dict(username='alice',   password='alice123',   email='alice@example.com',   role='user',  active=True),
    dict(username='bob',     password='bob123',     email='bob@example.com',     role='user',  active=True),
    dict(username='charlie', password='charlie123', email='charlie@example.com', role='user',  active=False),  # 禁用账号示例
]

# ── 软件访问控制 ─────────────────────────────────────────────

APP_ACCESS_CONFIG = [
    dict(app_name='MyEditor',  access_level='public'),      # 公开，无需登录
    dict(app_name='DataSync',  access_level='protected'),   # 需登录
    dict(app_name='QuickNote', access_level='restricted'),  # 仅指定用户
]

# restricted 软件的授权用户（用户名）
APP_ACCESS_GRANTS = {
    'QuickNote': ['alice'],  # bob 和 charlie 无权访问
}

# ── 版本数据 ────────────────────────────────────────────────

VERSIONS = [
    # ── MyEditor（公开）────────────────────────────────────
    dict(app_name='MyEditor', version='1.0.0', platform='windows',
         source='local', filename='MyEditor-1.0.0-windows.exe',
         file_size=45_234_688, sha256='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
         release_notes='初始发布版本', release_date=date(2025, 1, 10), mandatory=False),

    dict(app_name='MyEditor', version='1.0.0', platform='mac',
         source='local', filename='MyEditor-1.0.0-mac.dmg',
         file_size=52_428_800, sha256='b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3',
         release_notes='初始发布版本', release_date=date(2025, 1, 10), mandatory=False),

    dict(app_name='MyEditor', version='1.1.0', platform='windows',
         source='github',
         github_url='https://github.com/example/myeditor/releases/download/v1.1.0/MyEditor-1.1.0-windows.exe',
         file_size=46_800_000, sha256='c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4',
         release_notes='新增多标签页，修复崩溃问题', release_date=date(2025, 3, 5), mandatory=False),

    dict(app_name='MyEditor', version='1.1.0', platform='mac',
         source='github',
         github_url='https://github.com/example/myeditor/releases/download/v1.1.0/MyEditor-1.1.0-mac.dmg',
         file_size=53_000_000, sha256='d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5',
         release_notes='新增多标签页，修复崩溃问题', release_date=date(2025, 3, 5), mandatory=False),

    dict(app_name='MyEditor', version='1.2.0', platform='windows',
         source='github_proxy',
         github_url='https://github.com/example/myeditor/releases/download/v1.2.0/MyEditor-1.2.0-windows.exe',
         file_size=48_000_000, sha256='e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6',
         release_notes='性能大幅提升，新增插件系统', release_date=date(2025, 6, 20), mandatory=True),

    dict(app_name='MyEditor', version='1.2.0', platform='linux',
         source='github_proxy',
         github_url='https://github.com/example/myeditor/releases/download/v1.2.0/MyEditor-1.2.0-linux.tar.gz',
         file_size=41_000_000, sha256='f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1',
         release_notes='性能大幅提升，新增插件系统', release_date=date(2025, 6, 20), mandatory=True),

    # ── DataSync（需登录）───────────────────────────────────
    dict(app_name='DataSync', version='2.0.0', platform='windows',
         source='local', filename='DataSync-2.0.0-windows.msi',
         file_size=28_311_552, sha256='1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b',
         release_notes='重构核心同步引擎', release_date=date(2025, 2, 14), mandatory=False),

    dict(app_name='DataSync', version='2.0.0', platform='linux',
         source='local', filename='DataSync-2.0.0-linux.deb',
         file_size=25_165_824, sha256='2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c',
         release_notes='重构核心同步引擎', release_date=date(2025, 2, 14), mandatory=False),

    dict(app_name='DataSync', version='2.1.0', platform='windows',
         source='github_proxy',
         github_url='https://github.com/example/datasync/releases/download/v2.1.0/DataSync-2.1.0-windows.msi',
         file_size=29_000_000, sha256='3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d',
         release_notes='新增云端备份功能，修复断线重连 bug', release_date=date(2025, 5, 1), mandatory=False),

    dict(app_name='DataSync', version='2.1.0', platform='linux',
         source='github_proxy',
         github_url='https://github.com/example/datasync/releases/download/v2.1.0/DataSync-2.1.0-linux.deb',
         file_size=26_000_000, sha256='4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e',
         release_notes='新增云端备份功能，修复断线重连 bug', release_date=date(2025, 5, 1), mandatory=False),

    dict(app_name='DataSync', version='2.1.0', platform='mac',
         source='github',
         github_url='https://github.com/example/datasync/releases/download/v2.1.0/DataSync-2.1.0-mac.dmg',
         file_size=31_000_000, sha256='5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f',
         release_notes='新增云端备份功能，修复断线重连 bug', release_date=date(2025, 5, 1), mandatory=False),

    # ── QuickNote（受限）────────────────────────────────────
    dict(app_name='QuickNote', version='0.9.0', platform='windows',
         source='local', filename='QuickNote-0.9.0-windows.exe',
         file_size=8_388_608, sha256='6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a',
         release_notes='Beta 版本公测', release_date=date(2025, 4, 1), mandatory=False),

    dict(app_name='QuickNote', version='1.0.0', platform='windows',
         source='github_proxy',
         github_url='https://github.com/example/quicknote/releases/download/v1.0.0/QuickNote-1.0.0-windows.exe',
         file_size=9_000_000, sha256='a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3',
         release_notes='正式版发布，新增 Markdown 支持', release_date=date(2025, 7, 15), mandatory=True),

    dict(app_name='QuickNote', version='1.0.0', platform='mac',
         source='github_proxy',
         github_url='https://github.com/example/quicknote/releases/download/v1.0.0/QuickNote-1.0.0-mac.dmg',
         file_size=11_000_000, sha256='b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4',
         release_notes='正式版发布，新增 Markdown 支持', release_date=date(2025, 7, 15), mandatory=True),

    dict(app_name='QuickNote', version='1.0.0', platform='linux',
         source='github_proxy',
         github_url='https://github.com/example/quicknote/releases/download/v1.0.0/QuickNote-1.0.0-linux.AppImage',
         file_size=10_500_000, sha256='c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5',
         release_notes='正式版发布，新增 Markdown 支持', release_date=date(2025, 7, 15), mandatory=True),
]


# ── 辅助函数 ────────────────────────────────────────────────

def create_placeholder_file(app_name, platform, filename):
    """为 local 来源创建占位文件，避免下载时 404。"""
    import config
    path = os.path.join(config.UPLOAD_FOLDER, app_name, platform, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.write(b'[PLACEHOLDER] This is a seed file for testing.\n')
        return True
    return False


def seed_users():
    inserted = skipped = 0
    user_map = {}
    for u in USERS:
        existing = User.query.filter_by(username=u['username']).first()
        if existing:
            skipped += 1
            user_map[u['username']] = existing
        else:
            user = User(
                username=u['username'],
                email=u['email'],
                role=u['role'],
                active=u['active'],
            )
            user.set_password(u['password'])
            db.session.add(user)
            db.session.flush()  # 获取 id
            user_map[u['username']] = user
            inserted += 1
    db.session.commit()
    print(f'  用户    : 插入 {inserted} 条，跳过 {skipped} 条')
    return user_map


def seed_access_config():
    inserted = skipped = 0
    for item in APP_ACCESS_CONFIG:
        existing = db.session.get(AppConfig, item['app_name'])
        if existing:
            skipped += 1
        else:
            db.session.add(AppConfig(**item))
            inserted += 1
    db.session.commit()
    print(f'  访问配置: 插入 {inserted} 条，跳过 {skipped} 条')


def seed_access_grants(user_map):
    inserted = skipped = 0
    for app_name, usernames in APP_ACCESS_GRANTS.items():
        for username in usernames:
            user = user_map.get(username)
            if not user:
                continue
            existing = AppAccess.query.filter_by(app_name=app_name, user_id=user.id).first()
            if existing:
                skipped += 1
            else:
                db.session.add(AppAccess(app_name=app_name, user_id=user.id))
                inserted += 1
    db.session.commit()
    print(f'  访问授权: 插入 {inserted} 条，跳过 {skipped} 条')


def seed_versions():
    inserted = skipped = files_created = 0
    for item in VERSIONS:
        exists = AppVersion.query.filter_by(
            app_name=item['app_name'],
            version=item['version'],
            platform=item['platform'],
        ).first()
        if exists:
            skipped += 1
        else:
            db.session.add(AppVersion(**item))
            inserted += 1

        if item.get('source') == 'local' and item.get('filename'):
            if create_placeholder_file(item['app_name'], item['platform'], item['filename']):
                files_created += 1

    db.session.commit()
    print(f'  版本数据: 插入 {inserted} 条，跳过 {skipped} 条，创建占位文件 {files_created} 个')


def seed():
    app = create_app()
    with app.app_context():
        print('[Seed] 开始写入测试数据...')
        user_map = seed_users()
        seed_versions()
        seed_access_config()
        seed_access_grants(user_map)
        print('[Seed] 全部完成。\n')
        print('测试账号:')
        for u in USERS:
            status = '禁用' if not u['active'] else ('管理员' if u['role'] == 'admin' else '普通用户')
            print(f'  {u["username"]:10s} / {u["password"]:12s} [{status}]')
        print('\n软件访问控制:')
        print('  MyEditor   -> public     （任何人可访问）')
        print('  DataSync   -> protected  （需要登录）')
        print('  QuickNote  -> restricted （仅 alice + 管理员）')


if __name__ == '__main__':
    seed()