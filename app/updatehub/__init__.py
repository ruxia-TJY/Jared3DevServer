from flask import Blueprint

updatehub = Blueprint('updatehub', __name__, url_prefix='/updatehub')

from app.updatehub import views  # noqa: E402, F401
