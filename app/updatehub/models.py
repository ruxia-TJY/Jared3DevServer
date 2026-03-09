"""
app/updatehub/models.py - updatehub 数据模型。

数据表：
    app_version  - 软件各平台各版本的元数据（文件来源、哈希、发布说明等）。
    app_config   - 每款软件的访问级别配置（public / protected / restricted）。
    app_access   - restricted 级别软件的授权用户列表。

访问级别常量：
    ACCESS_PUBLIC     = 'public'      无需登录即可访问
    ACCESS_PROTECTED  = 'protected'   需要登录（任意已认证用户）
    ACCESS_RESTRICTED = 'restricted'  仅指定用户及管理员可访问
"""
from app.extensions import db

# 访问级别常量
ACCESS_PUBLIC     = 'public'      # 无需登录
ACCESS_PROTECTED  = 'protected'   # 需要登录（任何已认证用户）
ACCESS_RESTRICTED = 'restricted'  # 仅指定用户 + 管理员


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

    def to_dict(self, app_name=None):  # noqa: keep below AppConfig/AppAccess
        """将版本记录序列化为 API 响应字典。

        Args:
            app_name: 软件名称。传入时在返回字典中附加 ``download_url`` 字段。

        Returns:
            包含版本元数据的字典。local 来源含 ``filename``，
            github/github_proxy 来源含 ``github_url``。
        """
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


class AppConfig(db.Model):
    """每款软件的访问控制配置，无记录时默认 public。"""
    __tablename__ = 'app_config'

    app_name     = db.Column(db.String(64), primary_key=True,           comment='软件名称')
    access_level = db.Column(db.String(16), nullable=False,
                             default=ACCESS_PUBLIC,                      comment='访问级别')

    __table_args__ = ({'comment': '软件访问控制配置表'},)


class AppAccess(db.Model):
    """restricted 级别软件被授权访问的用户列表。"""
    __tablename__ = 'app_access'

    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    app_name = db.Column(db.String(64), nullable=False,                  comment='软件名称')
    user_id  = db.Column(db.Integer,
                         db.ForeignKey('user.id', ondelete='CASCADE'),
                         nullable=False,                                 comment='用户 ID')

    user = db.relationship('User', backref='app_accesses')

    __table_args__ = (
        db.UniqueConstraint('app_name', 'user_id', name='uq_app_access'),
        {'comment': '软件授权用户表'},
    )