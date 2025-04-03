document.addEventListener("DOMContentLoaded", function() {
    // گرفتن username از data-username
    const username = document.body.dataset.username;
    console.log("مقدار username:", username);

    const currentUser = document.body.dataset.currentUser;
    console.log("مقدار currentUser:", currentUser);

    const messagesDiv = document.getElementById('chat-messages');
    const userStatus = document.getElementById('user-status');
    const userStatusText = userStatus.querySelector('.status-text');
    const typingIndicator = document.getElementById('typing-indicator');
    const messageInput = document.getElementById('message-input');
    const messageStatus = document.getElementById('message-status');
    let typingTimeout;
    let lastSeenTimestamp = null;
    let updateInterval = null;
    let lastSentMessageId = null;

    // تابع اسکرول به پایین
    function scrollToBottom() {
        messagesDiv.scrollTop = 0;
    }

    // فرمت کردن زمان آخرین بازدید
    function formatLastSeen(timestamp) {
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diff = (now - date) / 1000;
        if (diff < 60) return "چند لحظه پیش";
        if (diff < 3600) return Math.floor(diff / 60) + " دقیقه پیش";
        if (diff < 86400) return Math.floor(diff / 3600) + " ساعت پیش";
        return date.toLocaleString('fa-IR', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' });
    }

    // تابع برای آپدیت زمان "چند لحظه پیش"
    function startLastSeenUpdate() {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
        updateInterval = setInterval(() => {
            if (lastSeenTimestamp && !userStatus.classList.contains("online")) {
                userStatusText.textContent = formatLastSeen(lastSeenTimestamp);
            }
        }, 5 * 60 * 1000);
    }

    // تابع برای آپدیت جهت متن
    function updateTextDirection(element, isPersian) {
        console.log("آپدیت جهت متن - فارسی؟", isPersian);
        if (isPersian) {
            element.classList.add('rtl', 'text-right');
            element.classList.remove('ltr', 'text-left');
            console.log("جهت تنظیم شد: rtl");
        } else {
            element.classList.add('ltr', 'text-left');
            element.classList.remove('rtl', 'text-right');
            console.log("جهت تنظیم شد: ltr");
        }
    }

    // تابع برای آپدیت وضعیت "دیده شد" یا "ارسال شد"
    function updateMessageStatus() {
        const messages = messagesDiv.querySelectorAll('.message.sent');
        if (messages.length === 0) {
            console.log("هیچ پیام ارسالی وجود ندارد، مخفی کردن message-status");
            messageStatus.classList.add('hidden');
            messageStatus.classList.remove('block');
            return;
        }

        const lastMessage = messages[0];
        const isRead = lastMessage.dataset.isRead === 'true';
        console.log(`آخرین پیام ارسالی - message_id: ${lastMessage.dataset.messageId}, is_read: ${isRead}`);
        messageStatus.textContent = isRead ? 'دیده شد' : 'ارسال شد';

        messageStatus.classList.remove('hidden');
        messageStatus.classList.add('block');
    }

    // تشخیص زبان ورودی با بررسی کل متن
    function detectLanguage(text) {
        if (!text) {
            return true;
        }

        const cleanText = text.replace(/[\s.,!?؟!()[\]{}<>،؛:]/g, '');
        if (!cleanText) {
            return true;
        }

        let persianCount = 0;
        let latinCount = 0;

        for (let char of cleanText) {
            const charCode = char.charCodeAt(0);
            if (charCode >= 0x0600 && charCode <= 0x06FF) {
                persianCount++;
            }
            else if ((charCode >= 0x0041 && charCode <= 0x005A) || (charCode >= 0x0061 && charCode <= 0x007A)) {
                latinCount++;
            }
        }

        console.log(`تشخیص زبان - متن: "${text}", تعداد حروف فارسی: ${persianCount}, تعداد حروف لاتین: ${latinCount}`);
        return persianCount >= latinCount;
    }

    // تابع برای ایجاد پیام جدید
    function createMessageElement(data) {
        const messageClass = data.sender === currentUser ? 'sent' : 'received';

        const messageDiv = document.createElement('div');
        messageDiv.className = `message mb-4 opacity-0 animate-slide-in ${messageClass}`;
        messageDiv.dataset.messageId = data.message_id || '';
        messageDiv.dataset.isRead = data.is_read ? 'true' : 'false';

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `bubble max-w-[70%] px-4 py-3 rounded-2xl shadow-sm ${
            messageClass === 'sent' ? 'bg-purple-800 text-white rounded-br-sm' : 'bg-white text-gray-800 rounded-bl-sm'
        }`;
        bubbleDiv.textContent = data.text;

        // تنظیم جهت متن پیام
        const isPersian = detectLanguage(data.text);
        updateTextDirection(bubbleDiv, isPersian);

        messageDiv.appendChild(bubbleDiv);

        const timeDiv = document.createElement('div');
        timeDiv.className = 'text-xs text-gray-500 mt-1';
        timeDiv.textContent = data.created_at ? data.created_at : 'زمان نامشخص';
        messageDiv.appendChild(timeDiv);

        return messageDiv;
    }

    // آپدیت جهت متن هنگام تایپ در textarea
    messageInput.addEventListener('input', function() {
        const text = this.value;
        const isPersian = detectLanguage(text);
        updateTextDirection(this, isPersian);
    });

    // تنظیم جهت اولیه برای textarea (پیش‌فرض فارسی)
    updateTextDirection(messageInput, true);

    // تنظیم جهت اولیه برای پیام‌های موجود در صفحه
    document.querySelectorAll('.message .bubble').forEach(bubble => {
        const text = bubble.textContent;
        const isPersian = detectLanguage(text);
        updateTextDirection(bubble, isPersian);
    });

    // ساخت آدرس WebSocket برای چت
    const chatSocket = new WebSocket(
        `ws://${window.location.host}/ws/chat/${username}/`
    );

    // ساخت آدرس WebSocket برای وضعیت کاربر
    const userStatusSocket = new WebSocket(
        `ws://${window.location.host}/ws/user_status/`
    );

    // گرفتن وضعیت اولیه کاربر
    fetch('/get_user_status/' + username + '/')
        .then(response => response.json())
        .then(data => {
            if (data.hide_online_status) {
                userStatusText.textContent = '';
                userStatus.classList.remove("online");
            } else if (data.is_online) {
                userStatusText.textContent = 'آنلاین';
                userStatus.classList.add("online");
            } else {
                lastSeenTimestamp = data.last_seen;
                userStatusText.textContent = formatLastSeen(lastSeenTimestamp);
                userStatus.classList.remove("online");
                startLastSeenUpdate();
            }
        })
        .catch(error => console.error("خطا در گرفتن وضعیت کاربر:", error));

    // WebSocket برای چت
    chatSocket.onopen = function() {
        console.log("اتصال به WebSocket چت برقرار شد");

        const receivedMessages = messagesDiv.querySelectorAll('.message.received');
        receivedMessages.forEach(message => {
            const messageId = message.dataset.messageId;
            if (messageId && message.dataset.isRead === 'false') {
                console.log(`ارسال پیام message_read برای message_id: ${messageId}`);
                chatSocket.send(JSON.stringify({
                    'type': 'message_read',
                    'message_id': messageId
                }));
            }
        });
    };

    chatSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("پیام دریافت شد:", data);
        console.log("نوع پیام (data.type):", data.type || "وجود ندارد");

        if (data.type.trim() === "chat_message") {
            console.log("کلاس پیام:", data.sender === currentUser ? "sent" : "received");
            console.log("زمان دریافت‌شده:", data.created_at);

            const messageElement = createMessageElement(data);
            messagesDiv.insertBefore(messageElement, messagesDiv.firstChild);
            scrollToBottom();

            const noMessages = messagesDiv.querySelector('.no-messages');
            if (noMessages) {
                noMessages.remove();
            }

            if (data.sender !== currentUser) {
                const audio = document.getElementById('notification-sound');
                audio.play().catch(error => console.error("Audio error:", error));
                if ('vibrate' in navigator) {
                    navigator.vibrate([200, 100, 200]);
                }

                if (data.is_read === false) {
                    console.log(`ارسال پیام message_read برای message_id: ${data.message_id}`);
                    chatSocket.send(JSON.stringify({
                        'type': 'message_read',
                        'message_id': data.message_id
                    }));
                }
            } else {
                lastSentMessageId = data.message_id;
            }

            updateMessageStatus();
        } else if (data.type.trim() === "typing") {
            console.log("پیام تایپینگ دریافت شد:", data);

            if (data.username === username) {
                if (data.is_typing) {
                    typingIndicator.classList.remove("opacity-0");
                    typingIndicator.classList.add("opacity-100");
                } else {
                    typingIndicator.classList.remove("opacity-100");
                    typingIndicator.classList.add("opacity-0");
                }
            }
        } else if (data.type.trim() === "message_read") {
            console.log("پیام دیده شد:", data);
            const message = messagesDiv.querySelector(`.message[data-message-id="${data.message_id}"]`);
            if (message) {
                message.dataset.isRead = 'true';
                console.log(`پیام ${data.message_id} به عنوان دیده شده آپدیت شد در کلاینت`);
                updateMessageStatus();
            } else {
                console.log(`پیام با message_id: ${data.message_id} در DOM پیدا نشد`);
            }
        } else {
            console.log("نوع پیام ناشناخته:", data.type);
        }
    };

    chatSocket.onerror = function(error) {
        console.error("خطا در WebSocket چت:", error);
    };

    chatSocket.onclose = function(event) {
        console.log("اتصال WebSocket چت بسته شد:", event);
        console.log("کد بسته شدن:", event.code, "دلیل:", event.reason);
    };

    // WebSocket برای وضعیت کاربر
    userStatusSocket.onopen = function() {
        console.log("اتصال به WebSocket وضعیت برقرار شد");
    };

    userStatusSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === "user_status" && data.username === username) {
            fetch('/get_user_status/' + username + '/')
                .then(response => response.json())
                .then(statusData => {
                    if (statusData.hide_online_status) {
                        userStatusText.textContent = '';
                        userStatus.classList.remove("online");
                    } else if (statusData.is_online) {
                        userStatusText.textContent = 'آنلاین';
                        userStatus.classList.add("online");
                        if (updateInterval) {
                            clearInterval(updateInterval);
                        }
                    } else {
                        lastSeenTimestamp = statusData.last_seen;
                        userStatusText.textContent = formatLastSeen(lastSeenTimestamp);
                        userStatus.classList.remove("online");
                        startLastSeenUpdate();
                    }
                })
                .catch(error => console.error("خطا در به‌روزرسانی وضعیت کاربر:", error));
        }
    };

    userStatusSocket.onclose = function(event) {
        console.log("اتصال WebSocket وضعیت بسته شد:", event);
    };

    // مدیریت ارسال پیام از فرم
    const messageForm = document.getElementById('message-form');
    if (!messageForm) {
        console.error("خطا: المنت messageForm پیدا نشد.");
        return;
    }

    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();

        if (message) {
            chatSocket.send(JSON.stringify({
                'type': 'chat_message',
                'message': message
            }));
            messageInput.value = '';
            messageInput.style.height = 'auto';
            updateTextDirection(messageInput, true);
        }
    });

    // ارسال پیام با Enter و رفتن به خط بعد با Shift+Enter
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            messageForm.dispatchEvent(new Event("submit"));
        }
    });

    // تنظیم خودکار ارتفاع textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // ارسال وضعیت تایپینگ
    messageInput.addEventListener('input', function() {
        clearTimeout(typingTimeout);
        chatSocket.send(JSON.stringify({
            'type': 'typing',
            'is_typing': true
        }));
        typingTimeout = setTimeout(() => {
            chatSocket.send(JSON.stringify({
                'type': 'typing',
                'is_typing': false
            }));
        }, 1000);
    });

    // اسکرول به پایین پیام‌ها هنگام لود صفحه
    scrollToBottom();

    // آپدیت اولیه وضعیت "دیده شد" یا "ارسال شد"
    updateMessageStatus();
});
