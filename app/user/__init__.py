from flask import Blueprint

user = Blueprint('user', __name__, url_prefix='/user')

from app.user import views  # noqa: E402, F401