let socket = null;
let currentChatUser = null;

// الاتصال بالسيرفر عبر WebSocket
function connectSocket() {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to chat server');
        loadChats();
    });
    
    socket.on('receive_message', (message) => {
        if (currentChatUser && message.sender_id === currentChatUser.id) {
            displayMessage(message);
            markMessageAsRead(message.id);
        } else {
            // إشعار بوجود رسالة جديدة
            showNotification('رسالة جديدة من ' + message.sender_name);
        }
        updateChatList();
    });
    
    socket.on('message_sent', (message) => {
        if (currentChatUser && message.receiver_id === currentChatUser.id) {
            displayMessage(message);
        }
    });
    
    socket.on('user_online', (user) => {
        updateUserStatus(user.user_id, true);
    });
    
    socket.on('user_offline', (user) => {
        updateUserStatus(user.user_id, false);
    });
}

// تحميل الدردشات
async function loadChats() {
    try {
        const response = await fetch('/api/users/search?q=');
        const users = await response.json();
        
        const chatList = document.getElementById('chatList');
        if (chatList) {
            chatList.innerHTML = users.map(user => `
                <div class="chat-item" onclick="openChat(${user.id})" data-user-id="${user.id}">
                    <div style="display: flex; align-items: center;">
                        <div class="profile-pic">
                            <img src="/static/images/${user.profile_pic || 'default.png'}" alt="${user.username}">
                        </div>
                        <div style="flex: 1;">
                            <h4>${user.username}</h4>
                            <p style="font-size: 0.9rem; color: #666;">${user.bio || 'لا يوجد وصف'}</p>
                        </div>
                        ${user.is_online ? 
                            '<span class="online-dot"></span>' : 
                            '<span style="color: #999; font-size: 0.8rem;">غير متصل</span>'
                        }
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading chats:', error);
    }
}

// فتح دردشة مع مستخدم
async function openChat(userId) {
    try {
        const response = await fetch(`/api/user/${userId}`);
        const user = await response.json();
        
        currentChatUser = user;
        
        // تحديث واجهة الدردشة
        document.getElementById('chatUserName').textContent = user.username;
        document.getElementById('chatUserStatus').innerHTML = user.is_online ? 
            '<span class="online-dot"></span> متصل الآن' : 
            `آخر ظهور: ${formatDate(user.last_seen)}`;
        
        // تحميل الرسائل
        await loadMessages(userId);
        
        // وضع التركيز على حقل الإدخال
        document.getElementById('messageInput').focus();
    } catch (error) {
        console.error('Error opening chat:', error);
    }
}

// تحميل الرسائل
async function loadMessages(userId) {
    try {
        const response = await fetch(`/api/messages/${userId}`);
        const messages = await response.json();
        
        const messagesContainer = document.getElementById('messagesContainer');
        messagesContainer.innerHTML = '';
        
        messages.forEach(message => {
            displayMessage(message);
        });
        
        // التمرير إلى الأسفل
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// عرض رسالة
function displayMessage(message) {
    const messagesContainer = document.getElementById('messagesContainer');
    const isSent = message.sender_id.toString() === localStorage.getItem('token');
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${isSent ? 'sent' : 'received'}`;
    messageElement.innerHTML = `
        <div class="message-content">
            ${message.message}
        </div>
        <div class="message-time">
            ${formatTime(message.timestamp)}
            ${message.is_read && isSent ? '<i class="fas fa-check-double" style="margin-right: 5px; color: #4CAF50;"></i>' : ''}
        </div>
    `;
    
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// إرسال رسالة
async function sendMessage() {
    if (!currentChatUser) {
        alert('يرجى اختيار مستخدم للدردشة');
        return;
    }
    
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    if (socket && socket.connected) {
        socket.emit('send_message', {
            receiver_id: currentChatUser.id,
            message: message
        });
        
        input.value = '';
    } else {
        alert('فقد الاتصال بالسيرفر. يرجى تحديث الصفحة.');
    }
}

// تحديث حالة المستخدم
function updateUserStatus(userId, isOnline) {
    const chatItem = document.querySelector(`.chat-item[data-user-id="${userId}"]`);
    if (chatItem) {
        const statusElement = chatItem.querySelector('.online-dot, span[style*="color: #999"]');
        if (isOnline) {
            statusElement.outerHTML = '<span class="online-dot"></span>';
        } else {
            statusElement.outerHTML = '<span style="color: #999; font-size: 0.8rem;">غير متصل</span>';
        }
    }
}

// تنسيق التاريخ والوقت
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ar-IQ', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ar-IQ', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// إشعارات
function showNotification(message) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification("عراقي شات", {
            body: message,
            icon: "/static/images/logo.png"
        });
    }
}

// طلب صلاحيات الإشعارات
if ("Notification" in window) {
    Notification.requestPermission();
}

// الاتصال بالسيرفر عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    connectSocket();
    
    // إرسال بالضغط على Enter
    document.getElementById('messageInput')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
