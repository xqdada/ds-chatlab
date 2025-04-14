 document.querySelector('#forgotPasswordForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const email = document.querySelector('#email').value.trim();
            const submitBtn = document.querySelector('#submitBtn');
            const submitText = document.querySelector('#submitText');
            const spinner = document.querySelector('#submitSpinner');
            const alertBox = document.querySelector('#alertMessage');

            // 验证邮箱格式
            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                showAlert('请输入有效的邮箱地址', 'danger');
                return;
            }

            // 显示加载状态
            submitBtn.disabled = true;
            submitText.textContent = '发送中...';
            spinner.classList.remove('d-none');
            alertBox.classList.add('d-none');

            try {
                const response = await fetch('/api/forgot-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email: email })
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert('密码重置邮件已发送，请检查您的邮箱', 'success');
                    document.querySelector('#forgotPasswordForm').reset();
                } else {
                    throw new Error(data.message || '请求失败');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert(error.message || '发送失败，请稍后重试', 'danger');
            } finally {
                submitBtn.disabled = false;
                submitText.textContent = '发送重置邮件';
                spinner.classList.add('d-none');
            }
        });

        function showAlert(message, type) {
            const alertBox = document.querySelector('#alertMessage');
            alertBox.textContent = message;
            alertBox.className = `alert alert-${type}`;
            alertBox.classList.remove('d-none');

            // 5秒后自动隐藏
            setTimeout(() => {
                alertBox.classList.add('d-none');
            }, 5000);
        }