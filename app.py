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
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # 注册蓝图
    from src.routers import auth
    app.register_blueprint(auth)

    # 初始化数据库
    @app.cli.command("init-db")
    def init_db():
        with app.app_context():
            db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(port=5001, debug=True)
