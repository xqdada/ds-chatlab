document.querySelector('#resetForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const password = document.querySelector('#password').value;
    const confirm = document.querySelector('#confirm_password').value;

    if (password !== confirm) {
        alert('两次输入的密码不一致');
        return;
    }

    try {
        const response = await fetch('/api/reset-password/' + document.querySelector('#token').value, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                password: password
            })
        });

        const result = await response.json();
        if (result.success) {
            alert('密码重置成功！');
            window.location.href = result.redirect || '/login';
        } else {
            alert('错误: ' + result.message);
        }
    } catch (error) {
        alert('请求失败，请重试');
    }
});