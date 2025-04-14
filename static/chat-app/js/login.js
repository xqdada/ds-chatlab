const passwordInput = document.querySelector('#password');
const togglePassword = document.querySelector('.toggle-password i');

togglePassword.addEventListener('click', function() {
    // 切换密码的显示/隐藏
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        togglePassword.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        togglePassword.classList.replace('fa-eye-slash', 'fa-eye');
    }
});
