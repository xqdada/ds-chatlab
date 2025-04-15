import os
from flask import Flask
from flask_cors import CORS
from src.extensions import db, bcrypt, migrate


def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    if os.path.exists('instance/config.py'):
        app.config.from_pyfile('instance/config.py')

    # 初始化扩展
    from src.extensions import init_ext
    init_ext(app)

    # 注册蓝图
    from src.routers import api_bp
    from src.views import auth_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    # 初始化数据库
    @app.cli.command("init-db")
    def init_db():
        with app.app_context():
            db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(port=5001, debug=True)
