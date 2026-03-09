"""
app/user/models.py - 系统用户数据模型。

User 表存储所有系统用户，支持管理员（admin）和普通用户（user）两种角色。
密码以 Werkzeug 生成的 bcrypt 哈希形式存储，不保存明文。
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model, UserMixin):
    """系统用户模型。

    Attributes:
        id           : 自增主键。
        username     : 唯一用户名，最长 64 个字符。
        email        : 可选邮箱，唯一，最长 128 个字符。
        password_hash: Werkzeug bcrypt 密码哈希，最长 256 个字符。
        role         : 用户角色，``'admin'`` 或 ``'user'``，默认 ``'user'``。
        active       : 账号是否启用，禁用账号无法登录。
        created_at   : 记录创建时间，由数据库自动填充。
    """
    __tablename__ = 'user'

    id            = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    username      = db.Column(db.String(64), nullable=False, unique=True,   comment='用户名')
    email         = db.Column(db.String(128),nullable=True,  unique=True,   comment='邮箱')
    password_hash = db.Column(db.String(256),nullable=False,               comment='密码哈希')
    role          = db.Column(db.String(16), nullable=False, default='user', comment='角色: admin/user')
    active        = db.Column(db.Boolean,    nullable=False, default=True,  comment='是否启用')
    created_at    = db.Column(db.DateTime,   nullable=False,
                              server_default=db.func.now(),                 comment='创建时间')

    __table_args__ = ({'comment': '系统用户表'},)

    @property
    def is_active(self):
        """账号是否处于启用状态（Flask-Login 接口）。

        Returns:
            ``True`` 表示账号已启用，可正常登录。
        """
        return self.active

    @property
    def is_admin(self):
        """是否为管理员角色。

        Returns:
            ``True`` 表示该用户拥有管理员权限。
        """
        return self.role == 'admin'

    def set_password(self, password: str) -> None:
        """将明文密码哈希化后保存到 ``password_hash`` 字段。

        Args:
            password: 用户输入的明文密码。
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """验证明文密码是否与已存储的哈希匹配。

        Args:
            password: 待验证的明文密码。

        Returns:
            密码正确时返回 ``True``，否则返回 ``False``。
        """
        return check_password_hash(self.password_hash, password)