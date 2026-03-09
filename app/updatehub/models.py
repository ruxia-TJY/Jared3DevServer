from app.extensions import db


class AppVersion(db.Model):
    """
    每条记录对应一个软件在特定平台的特定版本。
    唯一约束：(app_name, version, platform)
    """
    __tablename__ = 'app_version'

    id            = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    app_name      = db.Column(db.String(64), nullable=False, comment='软件名称')
    version       = db.Column(db.String(32), nullable=False, comment='版本号')
    platform      = db.Column(db.String(16), nullable=False, comment='平台: windows/mac/linux')

    # 来源：local / github / github_proxy
    source        = db.Column(db.String(16),  nullable=False, default='local',  comment='文件来源')

    # local 来源
    filename      = db.Column(db.String(256), nullable=True,                    comment='本地存储文件名')

    # github / github_proxy 来源
    github_url    = db.Column(db.String(512), nullable=True,                    comment='GitHub Release 文件直链')

    # 通用字段
    file_size     = db.Column(db.BigInteger,  nullable=False, default=0,        comment='文件大小（字节）')
    sha256        = db.Column(db.String(64),  nullable=False, default='',       comment='SHA256 校验值')
    release_notes = db.Column(db.Text,        nullable=False, default='',       comment='更新说明')
    release_date  = db.Column(db.Date,        nullable=True,                    comment='发布日期')
    mandatory     = db.Column(db.Boolean,     nullable=False, default=False,    comment='是否强制更新')
    created_at    = db.Column(db.DateTime,    nullable=False,
                              server_default=db.func.now(),                     comment='记录创建时间')

    __table_args__ = (
        db.UniqueConstraint('app_name', 'version', 'platform', name='uq_app_version_platform'),
        {'comment': '软件版本信息表'},
    )

    def to_dict(self, app_name=None):
        """转为 API 响应字典。传入 app_name 时附带 download_url。"""
        d = {
            'version':       self.version,
            'platform':      self.platform,
            'source':        self.source,
            'file_size':     self.file_size,
            'sha256':        self.sha256,
            'release_notes': self.release_notes,
            'release_date':  self.release_date.isoformat() if self.release_date else '',
            'mandatory':     self.mandatory,
        }
        if self.source == 'local':
            d['filename'] = self.filename
        else:
            d['github_url'] = self.github_url
        if app_name:
            d['download_url'] = (
                f'/updatehub/api/{app_name}/download'
                f'?platform={self.platform}&version={self.version}'
            )
        return d