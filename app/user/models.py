from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model, UserMixin):
    """
    系统用户。
    role: admin（管理员）/ user（普通用户）
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

    # Flask-Login 要求的 is_active 属性
    @property
    def is_active(self):
        return self.active

    @property
    def is_admin(self):
        return self.role == 'admin'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)