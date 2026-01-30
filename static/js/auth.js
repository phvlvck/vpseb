// تسجيل الدخول
async function login(username, password) {
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('token', data.user.id);
            localStorage.setItem('username', data.user.username);
            window.location.href = '/chat';
        } else {
            alert(data.message || 'خطأ في تسجيل الدخول');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('حدث خطأ في الاتصال بالسيرفر');
    }
}

// التسجيل
async function register(username, email, password) {
    if (!username || !email || !password) {
        alert('يرجى ملء جميع الحقول');
        return;
    }
    
    if (password.length < 6) {
        alert('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
        return;
    }
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('token', data.user.id);
            localStorage.setItem('username', data.user.username);
            window.location.href = '/chat';
        } else {
            alert(data.message || 'خطأ في التسجيل');
        }
    } catch (error) {
        console.error('Register error:', error);
        alert('حدث خطأ في الاتصال بالسيرفر');
    }
}

// تسجيل الخروج
async function logout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// التحقق من حالة الدخول
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token && !window.location.pathname.includes('/login') && 
        !window.location.pathname.includes('/register') && 
        window.location.pathname !== '/') {
        window.location.href = '/';
    }
}

// استدعاء التحقق عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', checkAuth);
