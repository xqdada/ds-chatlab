from flask import Blueprint, render_template, render_template_string
from flask import session, g
from src.extensions import db
from src.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/terms')
def terms_of_service():
    return render_template_string('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>服务条款 - 我的网站</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        .terms-container {
            max-width: 800px;
            margin: 30px auto;
            padding: 20px;
            background: #fff;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            border-radius: 5px;
        }
        .terms-content {
            max-height: 70vh;
            overflow-y: auto;
            padding: 15px;
            border: 1px solid #eee;
            margin-bottom: 20px;
            background: #f9f9f9;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        h2 {
            color: #3498db;
            margin-top: 25px;
        }
        .btn-accept {
            background-color: #3498db;
            color: white;
        }
        footer {
            margin-top: 30px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        @media (max-width: 768px) {
            .terms-container {
                margin: 10px;
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="terms-container">
        <h1>服务条款</h1>
        <p class="text-muted">最后更新日期：2023年11月15日</p>

        <div class="terms-content">
            <h2>1. 接受条款</h2>
            <p>通过访问和使用本网站，您同意遵守本服务条款的所有规定...</p>

            <h2>2. 服务描述</h2>
            <p>我们提供...服务，具体包括但不限于...</p>

            <h2>3. 用户义务</h2>
            <p>您同意不将本服务用于任何非法目的...</p>

            <h2>4. 隐私政策</h2>
            <p>您的隐私对我们很重要，请参阅我们的<a href="/privacy">隐私政策</a>...</p>

            <h2>5. 知识产权</h2>
            <p>本网站所有内容，包括但不限于文本、图形、标识...</p>

            <h2>6. 免责声明</h2>
            <p>本服务按"现状"提供，我们不做出任何明示或暗示的保证...</p>

            <h2>7. 责任限制</h2>
            <p>在任何情况下，我们都不对任何间接、附带、特殊...</p>

            <h2>8. 条款修改</h2>
            <p>我们保留随时修改这些条款的权利，修改后的条款将在发布后立即生效...</p>

            <h2>9. 终止</h2>
            <p>我们保留自行决定终止或暂停您访问服务的权利...</p>

            <h2>10. 适用法律</h2>
            <p>本条款受中华人民共和国法律管辖并按其解释...</p>
        </div>

        <div class="d-flex justify-content-between mt-4">
            <a href="/" class="btn btn-outline-secondary">返回首页</a>
            <!--div>
                <href="/privacy" class="btn btn-outline-primary me-2">隐私政策</a>
                <a href="/login" class="btn btn-accept">同意并继续</a>
            </div-->
        </div>

        <footer>
            <p>© 2023 我的公司 版权所有 | 联系方式: service@example.com</p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''')


@auth_bp.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')


@auth_bp.route('/register')
def register():
    return render_template('register.html')


@auth_bp.route('/index')
def index():
    return render_template('index.html')


@auth_bp.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id:
        user = db.session.get(User, user_id)
        setattr(g, "user", user)
    else:
        setattr(g, "user", None)


@auth_bp.context_processor
def inject_user_into_templates():
    return {"user": g.user}
