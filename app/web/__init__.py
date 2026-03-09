from flask import Blueprint

web = Blueprint('web', __name__, url_prefix='/updatehub')

from app.web import views  # noqa: E402, F401