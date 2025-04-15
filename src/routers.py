import logging
import string
import random
from functools import wraps

from flask import request, jsonify, session, url_for, make_response, g
from flask import Blueprint, current_app, render_template, redirect, render_template_string

from src.dk_client import LocalLLMClient, LocalLLMConfig
from src.extensions import db, mail
from src.models import User
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# 配置结构化日志（优化日志格式）
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("__name__")

api_bp = Blueprint('api', __name__)

# 验证码存储
captcha_store = {}


# 使用Redis或数据库存储
# import redis
# from datetime import timedelta
#
# captcha_store = redis.Redis(
#     host='localhost',
#     port=6379,
#     db=0,
#     decode_responses=True
# )
#
#
# def store_captcha(session_id, captcha_text, expire=300):
#     captcha_store.setex(session_id, timedelta(seconds=expire), captcha_text)
#
#
# def get_captcha(session_id):
#     return captcha_store.get(session_id)


@api_bp.route('/')
def home():
    return redirect('/login')


# 登录检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# 登录页面
@login_required
@api_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # 处理POST请求
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    captcha = data.get('captcha', '').lower()
    # remember = data.get('remember', False)

    # 验证验证码
    session_id = request.cookies.get('session') or request.remote_addr
    stored_captcha = captcha_store.pop(session_id, None)

    if not stored_captcha or captcha != stored_captcha:
        return jsonify({'success': False, 'message': '验证码错误'}), 400

    # 验证用户名和密码
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    # 登录成功
    session['user_id'] = user.id
    session['username'] = user.username

    response = jsonify({
        'success': True,
        'message': '登录成功',
        'redirect': url_for('auth.index')
    })

    # if remember:
    #     # 设置长期有效的session - 实际项目中应该设置合理的过期时间
    #     session.permanent = True

    return response


@api_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('api.login'))


def generate_captcha_text(length=None):
    """生成随机验证码文本"""
    if length is None:
        length = current_app.config['CAPTCHA_LENGTH']

    chars = string.ascii_uppercase + string.digits
    exclude_chars = {'0', 'O', '1', 'I', 'l', 'L', 'o'}
    chars = [c for c in chars if c not in exclude_chars]
    return ''.join(random.choices(chars, k=length))


def generate_captcha_image(text):
    """生成验证码图片"""
    length = current_app.config.get('CAPTCHA_LENGTH')
    width = current_app.config.get('CAPTCHA_WIDTH')
    height = current_app.config.get('CAPTCHA_HEIGHT')
    background = current_app.config.get('CAPTCHA_BACKGROUND')
    font_size = current_app.config.get('CAPTCHA_FONT_SIZE')
    font_colors = current_app.config.get('CAPTCHA_FONT_COLORS')
    noise_points = current_app.config.get('CAPTCHA_NOISE_POINTS')
    noise_lines = current_app.config.get('CAPTCHA_NOISE_LINES')
    image = Image.new('RGB', (width, height), background)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    # 绘制文本
    x = 10
    for char in text:
        color = random.choice(font_colors)
        y_offset = random.randint(-5, 5)
        draw.text((x, 10 + y_offset), char, fill=color, font=font)
        x += width // (length + 1)

    # 添加干扰
    for _ in range(noise_lines):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=random.choice(font_colors), width=1)

    for _ in range(noise_points):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=random.choice(font_colors)
        )

    image = image.filter(ImageFilter.SMOOTH)
    return image


@api_bp.route('/api/captcha')
def get_captcha():
    """获取验证码图片"""
    captcha_text = generate_captcha_text()
    session_id = request.cookies.get('session') or request.remote_addr
    captcha_store[session_id] = captcha_text.lower()

    image = generate_captcha_image(captcha_text)
    byte_io = BytesIO()
    image.save(byte_io, 'PNG')
    byte_io.seek(0)

    response = make_response(byte_io.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response


def get_serializer():
    """每次使用时动态获取"""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


@api_bp.route('/api/forgot-password', methods=['GET', 'POST'])
def api_forgot_password():
    """处理忘记密码的请求"""

    # 获取请求中的JSON数据
    data = request.get_json()
    # 检查数据是否存在且包含email字段
    if not data or 'email' not in data:
        return jsonify({"success": False, "message": "缺少邮箱参数"}), 400

    # 提取、整理email数据
    email = data['email'].strip().lower()

    # 1. 验证邮箱是否存在
    user = User.query.filter_by(email=email)
    if not user:
        return jsonify({
            "success": True,
            "message": "如果该邮箱已注册，重置链接将发送到您的邮箱"
        })

    # 2. 生成加密Token（包含邮箱和过期时间）
    try:
        serializer = get_serializer()
        token = serializer.dumps(
            email,
            salt=current_app.config['PASSWORD_RESET_SALT']
        )
    except Exception as e:
        logger.error(f"Token生成失败: {str(e)}")
        return jsonify({"success": False, "message": "系统错误"}), 500

    # 3. 发送密码重置邮件
    try:
        reset_url = url_for(
            'api.reset_password',
            token=token,
            _external=True
        )
        msg = Message(
            subject="DeepSeek聊天室密码重置",
            recipients=[email],
            html=f'''
            <h3>密码重置请求</h3>
            <p>请点击以下链接重置您的密码（有效期1小时）：</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>如果您未请求重置密码，请忽略此邮件。</p>
            <hr>
            <small>DeepSeek团队</small>
            '''
        )
        mail.send(msg)
    except Exception as e:
        logger.error(f"邮件发送失败: {str(e)}")
        return jsonify({"success": False, "message": "邮件发送失败"}), 500

    # 返回成功响应
    return jsonify({
        "success": True,
        "message": "重置链接已发送到您的邮箱"
    })


@api_bp.route('/api/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """处理密码重置请求"""

    # 创建一个序列化器对象，用于解码和验证令牌
    serializer = get_serializer()

    try:
        # 尝试从令牌中加载用户的电子邮件地址，同时检查令牌是否过期
        email = serializer.loads(
            token,
            salt=current_app.config['PASSWORD_RESET_SALT'],
            max_age=current_app.config['PASSWORD_RESET_EXPIRE']
        )
        # 查询数据库以获取用户对象
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("用户不存在")

    except (SignatureExpired, BadSignature) as e:
        # 如果令牌过期或无效，根据请求方法返回相应的响应
        if request.method == 'GET':
            # 对于GET请求，尝试从令牌中加载电子邮件地址（不检查过期时间）
            email = serializer.loads(
                token,
                salt=current_app.config['PASSWORD_RESET_SALT']
            )
            # 返回密码重置令牌过期页面
            return render_template('reset_password_expired.html', email=email, token=token)

        # 对于POST请求，返回错误信息
        return jsonify({"success": False, "message": str(e)}), 400

    # 处理GET请求，返回密码重置页面
    if request.method == 'GET':
        return render_template('reset_password.html',
                               email=email,
                               token=token)

    # 处理POST请求，获取新密码
    data = request.get_json()
    if not data or 'password' not in data:
        # 如果未提供新密码，返回错误信息
        return jsonify({"success": False, "message": "需要提供新密码"}), 400

    try:
        # 更新用户密码并提交到数据库
        user.set_password(data['password'])
        db.session.commit()
        # 返回成功信息和登录页面的重定向URL
        return jsonify({
            "success": True,
            "message": "密码已重置",
            "redirect": url_for('api.login')
        })
    except Exception as e:
        # 如果密码更新失败，回滚数据库更改并记录错误日志
        db.session.rollback()
        logger.error(f"密码重置失败: {str(e)}")
        # 返回错误信息
        return jsonify({"success": False, "message": "密码更新失败"}), 500


def validate_registration(data):
    errors = {}
    if User.query.filter_by(username=data['username']).first():
        errors['username'] = '用户名已存在'
    if User.query.filter_by(email=data['email']).first():
        errors['email'] = '邮箱已被注册'
    if len(data['password']) < 8:
        errors['password'] = '密码至少需要8个字符'
    if data['password'] != data.get('confirm_password'):
        errors['confirm_password'] = '密码不一致'
    return errors


@api_bp.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    # 验证数据
    errors = validate_registration(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        new_user = User(
            username=data['username'],
            email=data['email']
        )
        new_user.set_password(data['password'])

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'message': '注册成功',
            'user': {
                'id': new_user.id,
                'username': new_user.username
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '注册失败，请稍后重试'}), 500


class APIConnectionError(Exception):
    def __init__(self, message: str):
        super().__init__(f"[API连接异常] {message}")


def handle_api_errors(f):
    """装饰器用于统一处理API错误"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIConnectionError as e:
            logger.error(f"API连接错误: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': '无法连接到AI服务，请稍后再试',
                'error': str(e)
            }), 503
        except Exception as e:
            logger.error(f"未处理的异常: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': '处理请求时发生内部错误',
                'error': str(e)
            }), 500

    return wrapper


def validate_chat_request(data):
    """验证聊天请求数据"""
    if not data:
        return False, "请求体不能为空"

    message = data.get('message')
    if not message or not isinstance(message, str):
        return False, "消息内容无效或缺失"

    return True, {'message': message, 'username': 'user'}


@api_bp.route('/api/chat', methods=['POST'])
@handle_api_errors
def chat_api():
    """处理聊天API请求 """

    # 1. 验证请求数据
    is_valid, validation_result = validate_chat_request(request.get_json())
    if not is_valid:
        return jsonify({
            'status': 'error',
            'message': validation_result
        }), 400

    message_data = validation_result

    # 2. 初始化LLM配置
    config = LocalLLMConfig(
        endpoint=current_app.config['DEFAULT_ENDPOINT'],
        model_name=current_app.config['DEFAULT_MODEL'],
        temperature=current_app.config['DEFAULT_TEMPERATURE']
    )

    # 3. 创建客户端并生成响应
    client = LocalLLMClient(config)
    messages = [{"role": message_data['username'], "content": message_data['message']}]

    try:
        response = client.generate(messages=messages)
        result = next(response)

        # 4. 验证并处理响应
        if not result or not isinstance(result, dict):
            raise ValueError("无效的API响应格式")

        content = result.get('message', {}).get('content', '')
        if not content:
            logger.warning("收到空响应内容", extra={"response": result})
            content = "抱歉，我无法理解这个问题。"

        # 5. 返回成功响应
        return jsonify({
            'response': content,
            'status': 'success',
            'model': current_app.config['DEFAULT_MODEL']
        })

    except StopIteration:
        logger.error("API响应为空")
        return jsonify({
            'status': 'error',
            'message': 'AI服务未返回有效响应'
        }), 503


# 错误处理
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': '资源未找到'}), 404


@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500
