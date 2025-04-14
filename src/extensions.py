# Flask扩展初始化

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
mail = Mail()

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379/0")


def init_limiter(app):
    limiter.init_app(app)
