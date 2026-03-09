"""
seed.py - 向数据库插入示例数据，用于开发测试。
运行方式：python seed.py
"""
import os
from datetime import date
from app import create_app
from app.extensions import db
from app.models import AppVersion

SEED_DATA = [
    # ── MyEditor ──────────────────────────────────────────
    dict(app_name='MyEditor', version='1.0.0', platform='windows',
         source='local', filename='MyEditor-1.0.0-windows.exe',
         file_size=45_234_688, sha256='a1b2c3d4e5f6' * 5 + 'a1b2',
         release_notes='初始发布版本', release_date=date(2025, 1, 10), mandatory=False),

    dict(app_name='MyEditor', version='1.0.0', platform='mac',
         source='local', filename='MyEditor-1.0.0-mac.dmg',
         file_size=52_428_800, sha256='b2c3d4e5f6a1' * 5 + 'b2c3',
         release_notes='初始发布版本', release_date=date(2025, 1, 10), mandatory=False),

    dict(app_name='MyEditor', version='1.1.0', platform='windows',
         source='github',
         github_url='https://github.com/example/myeditor/releases/download/v1.1.0/MyEditor-1.1.0-windows.exe',
         file_size=46_800_000, sha256='c3d4e5f6a1b2' * 5 + 'c3d4',
         release_notes='新增多标签页，修复崩溃问题', release_date=date(2025, 3, 5), mandatory=False),

    dict(app_name='MyEditor', version='1.1.0', platform='mac',
         source='github',
         github_url='https://github.com/example/myeditor/releases/download/v1.1.0/MyEditor-1.1.0-mac.dmg',
         file_size=53_000_000, sha256='d4e5f6a1b2c3' * 5 + 'd4e5',
         release_notes='新增多标签页，修复崩溃问题', release_date=date(2025, 3, 5), mandatory=False),

    dict(app_name='MyEditor', version='1.2.0', platform='windows',
         source='github_proxy',
         github_url='https://github.com/example/myeditor/releases/download/v1.2.0/MyEditor-1.2.0-windows.exe',
         file_size=48_000_000, sha256='e5f6a1b2c3d4' * 5 + 'e5f6',
         release_notes='性能大幅提升，新增插件系统', release_date=date(2025, 6, 20), mandatory=True),

    dict(app_name='MyEditor', version='1.2.0', platform='linux',
         source='github_proxy',
         github_url='https://github.com/example/myeditor/releases/download/v1.2.0/MyEditor-1.2.0-linux.tar.gz',
         file_size=41_000_000, sha256='f6a1b2c3d4e5' * 5 + 'f6a1',
         release_notes='性能大幅提升，新增插件系统', release_date=date(2025, 6, 20), mandatory=True),

    # ── DataSync ──────────────────────────────────────────
    dict(app_name='DataSync', version='2.0.0', platform='windows',
         source='local', filename='DataSync-2.0.0-windows.msi',
         file_size=28_311_552, sha256='1a2b3c4d5e6f' * 5 + '1a2b',
         release_notes='重构核心同步引擎', release_date=date(2025, 2, 14), mandatory=False),

    dict(app_name='DataSync', version='2.0.0', platform='linux',
         source='local', filename='DataSync-2.0.0-linux.deb',
         file_size=25_165_824, sha256='2b3c4d5e6f1a' * 5 + '2b3c',
         release_notes='重构核心同步引擎', release_date=date(2025, 2, 14), mandatory=False),

    dict(app_name='DataSync', version='2.1.0', platform='windows',
         source='github_proxy',
         github_url='https://github.com/example/datasync/releases/download/v2.1.0/DataSync-2.1.0-windows.msi',
         file_size=29_000_000, sha256='3c4d5e6f1a2b' * 5 + '3c4d',
         release_notes='新增云端备份功能，修复断线重连 bug', release_date=date(2025, 5, 1), mandatory=False),

    dict(app_name='DataSync', version='2.1.0', platform='linux',
         source='github_proxy',
         github_url='https://github.com/example/datasync/releases/download/v2.1.0/DataSync-2.1.0-linux.deb',
         file_size=26_000_000, sha256='4d5e6f1a2b3c' * 5 + '4d5e',
         release_notes='新增云端备份功能，修复断线重连 bug', release_date=date(2025, 5, 1), mandatory=False),

    dict(app_name='DataSync', version='2.1.0', platform='mac',
         source='github',
         github_url='https://github.com/example/datasync/releases/download/v2.1.0/DataSync-2.1.0-mac.dmg',
         file_size=31_000_000, sha256='5e6f1a2b3c4d' * 5 + '5e6f',
         release_notes='新增云端备份功能，修复断线重连 bug', release_date=date(2025, 5, 1), mandatory=False),

    # ── QuickNote ─────────────────────────────────────────
    dict(app_name='QuickNote', version='0.9.0', platform='windows',
         source='local', filename='QuickNote-0.9.0-windows.exe',
         file_size=8_388_608, sha256='6f1a2b3c4d5e' * 5 + '6f1a',
         release_notes='Beta 版本公测', release_date=date(2025, 4, 1), mandatory=False),

    dict(app_name='QuickNote', version='1.0.0', platform='windows',
         source='github_proxy',
         github_url='https://github.com/example/quicknote/releases/download/v1.0.0/QuickNote-1.0.0-windows.exe',
         file_size=9_000_000, sha256='a2b3c4d5e6f1' * 5 + 'a2b3',
         release_notes='正式版发布，新增 Markdown 支持', release_date=date(2025, 7, 15), mandatory=True),

    dict(app_name='QuickNote', version='1.0.0', platform='mac',
         source='github_proxy',
         github_url='https://github.com/example/quicknote/releases/download/v1.0.0/QuickNote-1.0.0-mac.dmg',
         file_size=11_000_000, sha256='b3c4d5e6f1a2' * 5 + 'b3c4',
         release_notes='正式版发布，新增 Markdown 支持', release_date=date(2025, 7, 15), mandatory=True),

    dict(app_name='QuickNote', version='1.0.0', platform='linux',
         source='github_proxy',
         github_url='https://github.com/example/quicknote/releases/download/v1.0.0/QuickNote-1.0.0-linux.AppImage',
         file_size=10_500_000, sha256='c4d5e6f1a2b3' * 5 + 'c4d5',
         release_notes='正式版发布，新增 Markdown 支持', release_date=date(2025, 7, 15), mandatory=True),
]


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


def seed():
    app = create_app()
    with app.app_context():
        inserted  = 0
        skipped   = 0
        files_created = 0

        for item in SEED_DATA:
            exists = AppVersion.query.filter_by(
                app_name=item['app_name'],
                version=item['version'],
                platform=item['platform'],
            ).first()
            if exists:
                skipped += 1
            else:
                row = AppVersion(**item)
                db.session.add(row)
                inserted += 1

            # local 来源：确保磁盘上有文件
            if item.get('source') == 'local' and item.get('filename'):
                created = create_placeholder_file(
                    item['app_name'], item['platform'], item['filename']
                )
                if created:
                    files_created += 1

        db.session.commit()
        print(f'[Seed] 完成：插入 {inserted} 条，跳过已存在 {skipped} 条，创建占位文件 {files_created} 个')


if __name__ == '__main__':
    seed()