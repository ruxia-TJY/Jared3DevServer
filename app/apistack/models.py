"""
app/apistack/models.py - API Stack 数据模型。

表结构：
    api_entry  —— API 注册表，每行对应一个可调用的 API 端点
    api_token  —— 私有 API 的访问凭证，支持一个 API 绑定多个 Token

文档渲染策略（写时计算，读时直取）：
    - doc_content 存储 Markdown 源文件，由管理员编辑
    - doc_html    存储预渲染的 HTML，在每次保存 doc_content 时由 render_doc() 生成
    - 读取文档时直接使用 doc_html，零 CPU 开销
"""
import markdown as md_lib
from markupsafe import Markup

from app.extensions import db

# Markdown 渲染扩展列表
_MD_EXTENSIONS = ['tables', 'fenced_code', 'nl2br', 'toc']


class ApiEntry(db.Model):
    """API 注册条目。

    记录一个 API 端点的全部元信息，包括可见性控制（public / private）
    和以 Markdown 存储的使用文档。

    Attributes:
        id:           主键，自增整数。
        name:         URL 标识符，区分大小写，对应路由中的 <api_name>。
        display_name: 人类可读的显示名称。
        description:  一句话功能描述，用于文档列表页摘要。
        author:       API 作者，可选。
        version:      版本号字符串（如 "1.0.0"），不做语义化校验。
        visibility:   访问控制策略。"public" 任何人可访问；
                      "private" 需要在请求中携带有效 Token。
        enabled:      是否启用。禁用时执行端点返回 403。
        doc_content:  Markdown 格式的使用文档源文件，由管理员编写。
        doc_html:     由 doc_content 预渲染的 HTML，通过 render_doc() 生成。
        created_at:   记录创建时间，数据库服务端自动填充。
        updated_at:   记录最后更新时间，每次写入时自动刷新。
        tokens:       关联的 ApiToken 列表（仅 private API 使用）。
    """

    __tablename__ = 'api_entry'

    id           = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    name         = db.Column(db.String(64),  nullable=False, unique=True,
                             comment='URL 标识符，对应 /apistack/api/<name>')
    display_name = db.Column(db.String(128), nullable=False, comment='显示名称')
    description  = db.Column(db.Text,        nullable=True,  comment='一句话功能描述')
    author       = db.Column(db.String(64),  nullable=True,  comment='作者')
    version      = db.Column(db.String(32),  nullable=False, default='1.0.0', comment='版本号')
    visibility   = db.Column(db.String(16),  nullable=False, default='public',
                             comment='public=公开；private=需 Token')
    enabled      = db.Column(db.Boolean,     nullable=False, default=True,  comment='是否启用')
    doc_content  = db.Column(db.Text,        nullable=True,
                             comment='使用文档 Markdown 源文件，由管理员编写')
    doc_html     = db.Column(db.Text,        nullable=True,
                             comment='预渲染 HTML，由 render_doc() 在写入时生成')
    created_at   = db.Column(db.DateTime,    nullable=False, server_default=db.func.now())
    updated_at   = db.Column(db.DateTime,    nullable=False, server_default=db.func.now(),
                             onupdate=db.func.now())

    tokens = db.relationship('ApiToken', backref='api', cascade='all, delete-orphan',
                             lazy='select')

    __table_args__ = ({'comment': 'API 注册表'},)

    # ── 方法 ──────────────────────────────────────────────────────────────────

    def render_doc(self) -> None:
        """将 doc_content（Markdown）渲染为 HTML 并写入 doc_html。

        应在每次更新 doc_content 后、db.session.commit() 之前调用。
        若 doc_content 为空，则将 doc_html 置为 None。

        启用扩展：tables / fenced_code / nl2br / toc。
        """
        if self.doc_content:
            self.doc_html = md_lib.markdown(self.doc_content, extensions=_MD_EXTENSIONS)
        else:
            self.doc_html = None

    @property
    def rendered_doc(self):
        """返回可安全嵌入 Jinja2 模板的 Markup 对象。

        直接使用预渲染的 doc_html，不触发任何计算。

        Returns:
            Markup: 已转义安全的 HTML 字符串；若文档为空则返回 None。
        """
        return Markup(self.doc_html) if self.doc_html else None

    @property
    def url(self) -> str:
        """API 执行端点的相对路径。

        Returns:
            str: 形如 ``/apistack/api/<name>`` 的路径字符串。
        """
        return f'/apistack/api/{self.name}'

    def to_dict(self) -> dict:
        """序列化为字典，用于 JSON 响应。

        Returns:
            dict: 包含 name、display_name、description、author、version、
                  visibility、url、enabled、created_at、updated_at 的字典。
                  不含 doc_content / doc_html（文档通过独立端点获取）。
        """
        return {
            'name':         self.name,
            'display_name': self.display_name,
            'description':  self.description,
            'author':       self.author,
            'version':      self.version,
            'visibility':   self.visibility,
            'url':          self.url,
            'enabled':      self.enabled,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
            'updated_at':   self.updated_at.isoformat() if self.updated_at else None,
        }


class ApiToken(db.Model):
    """私有 API 的访问凭证。

    一个 ApiEntry 可绑定多个 Token，便于向不同使用方分发独立凭证，
    吊销时互不影响。

    Attributes:
        id:         主键，自增整数。
        api_id:     关联的 ApiEntry 主键（外键）。
        token:      48 位十六进制随机字符串，全表唯一。
        label:      备注，用于标识该 Token 的使用方（如"iOS 客户端"）。
        created_at: 生成时间，数据库服务端自动填充。
    """

    __tablename__ = 'api_token'

    id         = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    api_id     = db.Column(db.Integer,    db.ForeignKey('api_entry.id'), nullable=False)
    token      = db.Column(db.String(64), nullable=False, unique=True, comment='访问 Token')
    label      = db.Column(db.String(64), nullable=True,  comment='备注（使用方标识）')
    created_at = db.Column(db.DateTime,   nullable=False, server_default=db.func.now())

    __table_args__ = ({'comment': 'API 访问 Token'},)