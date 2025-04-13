document.addEventListener('DOMContentLoaded', function() {
    // 登录表单处理
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // 注册表单处理
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }

    // 验证码点击刷新
    const captchaImg = document.querySelector('.captcha-img');
    if (captchaImg) {
        captchaImg.addEventListener('click', function() {
            this.src = '/api/captcha?t=' + Date.now();
        });
    }

    // 检查用户是否已登录
    // checkAuthStatus();
});

// 处理登录
async function handleLogin(e) {
    e.preventDefault();

    const form = e.target;
    const username = form.querySelector('#username').value;
    const password = form.querySelector('#password').value;
    const captcha = form.querySelector('#captcha')?.value;
    const remember = form.querySelector('#remember')?.checked || false;

    // 简单前端验证
    if (!username || !password) {
        showAlert('请输入用户名和密码', 'error');
        return;
    }

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                password,
                captcha,
                remember
            }),
            credentials: 'include' // 包含 cookies
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '登录失败');
        }

        // 登录成功处理
        localStorage.setItem('user', JSON.stringify(data.user));

        showAlert('登录成功', 'success');

        // 重定向到首页或原请求页面
        const redirectUrl = new URLSearchParams(window.location.search).get('redirect') || '/index';
        window.location.href = redirectUrl;

    } catch (error) {
        console.error('登录错误:', error);
        showAlert(error.message || '登录过程中发生错误', 'error');
        // 刷新验证码
        const captchaImg = document.querySelector('.captcha-img');
        if (captchaImg) captchaImg.click();
    }
}

// 处理注册
async function handleRegister(e) {
    e.preventDefault();

    const form = e.target;
    const username = form.querySelector('#regUsername').value;
    const email = form.querySelector('#regEmail').value;
    const password = form.querySelector('#regPassword').value;
    const confirmPassword = form.querySelector('#regConfirmPassword').value

    // 简单前端验证
    if (password !== confirmPassword) {
        showAlert('两次输入的密码不一致', 'error');
        return;
    }

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                email,
                password,
                confirm_password: confirmPassword
            })
        });

        const data = await response.json();

        if (!response.ok) {
            // 处理验证错误
            if (data.errors) {
                let errorMsg = '';
                for (const [field, msg] of Object.entries(data.errors)) {
                    errorMsg += `${field}: ${msg}\n`;
                }
                throw new Error(errorMsg);
            }
            throw new Error(data.error || '注册失败');
        }

        // 注册成功处理
        showAlert('注册成功，请登录', 'success');

        // 自动填充用户名并跳转到登录页
        setTimeout(() => {
            window.location.href = `/login?username=${encodeURIComponent(username)}`;
        }, 1500);

    } catch (error) {
        console.error('注册错误:', error);
        showAlert(error.message || '注册过程中发生错误', 'error');
    }
}


// 更新认证后的UI
function updateAuthUI(user) {
    const authLinks = document.querySelector('.auth-links');
    const userInfo = document.querySelector('.user-info');

    if (authLinks && userInfo) {
        authLinks.style.display = 'none';
        userInfo.style.display = 'block';
        userInfo.querySelector('.username').textContent = user.username;
    }
}

// 显示提示信息
function showAlert(message, type = 'info') {
    alert(`${type.toUpperCase()}: ${message}`);
}
