// chatbox/static/chatbox/js/chat.js

document.addEventListener("DOMContentLoaded", function() {
    console.log("فایل chat.js با موفقیت لود شد");

    // گرفتن username و currentUser از data-username و data-current-user
    const username = document.body.dataset.username;
    console.log("مقدار username:", username);

    const currentUser = document.body.dataset.currentUser;
    console.log("مقدار currentUser:", currentUser);

    const isBlocked = document.body.dataset.isBlocked === 'true';
    const isBlockedByMe = document.body.dataset.isBlockedByMe === 'true';
    const isBlockedByOther = document.body.dataset.isBlockedByOther === 'true';

    // گرفتن المنت‌ها
    const messagesDiv = document.getElementById('chat-messages');
    const userStatusIndicator = document.getElementById('user-status-indicator');
    const userStatusDot = document.getElementById('user-status-dot');
    const userStatusText = document.getElementById('user-status-text');
    const typingIndicator = document.getElementById('typing-indicator');
    const messageInput = document.getElementById('message-input'); // ممکنه null باشه
    const messageForm = document.getElementById('message-form');   // ممکنه null باشه
    const blockStatusDiv = document.getElementById('block-status');
    const blockMessageP = document.getElementById('block-message');
    const chatBoxDiv = document.getElementById('chat-box');
    const blockButton = document.getElementById('block-button');
    const unblockButton = document.getElementById('unblock-button');
    const profileModal = document.getElementById('profile-modal');
    const profileMainPhoto = document.getElementById('profile-main-photo');
    const profileUsername = document.getElementById('profile-username');
    const profilePhone = document.getElementById('profile-phone');
    const profileEmail = document.getElementById('profile-email');
    const profileBio = document.getElementById('profile-bio');
    const profileDateJoined = document.getElementById('profile-date-joined');
    const photoModal = document.getElementById('photo-modal');
    const photoModalImage = document.getElementById('photo-modal-image');

    // چک کردن فقط المنت‌های ضروری
    if (!messagesDiv) {
        console.error("خطا: المنت messagesDiv پیدا نشد.");
        return;
    }

    if (!userStatusIndicator || !userStatusDot || !userStatusText || !typingIndicator || !blockStatusDiv || !blockMessageP || !chatBoxDiv || !blockButton || !unblockButton || !profileModal || !photoModal) {
        console.error("خطا: یکی از المنت‌های مورد نیاز پیدا نشد.");
        console.log("messagesDiv:", messagesDiv);
        console.log("userStatusIndicator:", userStatusIndicator);
        console.log("userStatusDot:", userStatusDot);
        console.log("userStatusText:", userStatusText);
        console.log("typingIndicator:", typingIndicator);
        console.log("messageInput:", messageInput);
        console.log("messageForm:", messageForm);
        console.log("blockStatusDiv:", blockStatusDiv);
        console.log("blockMessageP:", blockMessageP);
        console.log("chatBoxDiv:", chatBoxDiv);
        console.log("blockButton:", blockButton);
        console.log("unblockButton:", unblockButton);
        console.log("profileModal:", profileModal);
        console.log("photoModal:", photoModal);
        return;
    }

    let typingTimeout;
    let lastSeenTimestamp = null;
    let updateInterval = null;
    let receiverAlwaysKeepUnread = false;
    let currentPhotoIndex = 0;
    let photos = [];

    // تابع برای گرفتن CSRF Token
    function getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                return cookie.substring(name.length + 1);
            }
        }
        return '';
    }

    // تابع برای مدیریت نمایش دکمه‌ها
    function updateBlockButtons(isBlockedByMe) {
        if (blockButton && unblockButton) {
            if (isBlockedByMe) {
                blockButton.classList.add('hidden');
                unblockButton.classList.remove('hidden');
            } else {
                blockButton.classList.remove('hidden');
                unblockButton.classList.add('hidden');
            }
        }
    }

    // تابع برای آپدیت رابط کاربری در حالت بلاک
    function updateBlockUI(isBlocked, isBlockedByMe, isBlockedByOther) {
        document.body.dataset.isBlocked = isBlocked ? 'true' : 'false';
        document.body.dataset.isBlockedByMe = isBlockedByMe ? 'true' : 'false';
        document.body.dataset.isBlockedByOther = isBlockedByOther ? 'true' : 'false';
        updateBlockButtons(isBlockedByMe);

        if (isBlockedByOther) {
            blockStatusDiv.innerHTML = '<p class="text-sm text-red-500">شما توسط این کاربر بلاک شده‌اید</p>';
        } else {
            blockStatusDiv.innerHTML = '';
        }

        if (isBlockedByMe) {
            blockMessageP.innerHTML = '<p class="text-center text-red-500">شما این کاربر را بلاک کرده‌اید.</p>';
        } else {
            blockMessageP.innerHTML = '';
        }

        if (isBlocked) {
            chatBoxDiv.innerHTML = '<div class="bg-white p-3 border-t border-gray-200 text-center text-red-500 flex justify-center items-center">شما نمی‌توانید به این کاربر پیام بفرستید.</div>';
            userStatusIndicator.classList.remove("online");
            userStatusIndicator.classList.add("offline");
            userStatusDot.classList.remove("online");
            userStatusDot.classList.add("offline");
            userStatusText.textContent = "چند لحظه پیش";
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        } else {
            chatBoxDiv.innerHTML = `
                <div class="bg-white p-3 border-t border-gray-200 flex items-center gap-3">
                    <form id="message-form" class="flex-1 flex gap-3">
                        <textarea id="message-input" name="message" placeholder="پیام خود را بنویسید..." rows="1"
                                  class="flex-1 w-full p-2 border border-gray-300 rounded-full text-sm h-[40px] resize-none overflow-y-auto focus:outline-none focus:border-purple-800 focus:ring-2 focus:ring-purple-200 font-sans"></textarea>
                        <button type="submit" class="w-10 h-10 flex items-center justify-center bg-purple-800 text-white rounded-full hover:bg-purple-900 transition-colors">
                            <i class="fas fa-arrow-up"></i>
                        </button>
                    </form>
                    <div class="flex gap-3">
                        <a href="#" class="text-xl text-gray-500" id="mic-icon"><i class="fas fa-microphone"></i></a>
                        <a href="#" class="text-xl text-gray-500" id="gallery-icon"><i class="fas fa-image"></i></a>
                    </div>
                </div>
            `;
            const newMessageForm = document.getElementById('message-form');
            const newMessageInput = document.getElementById('message-input');
            if (newMessageForm && newMessageInput) {
                newMessageForm.addEventListener('submit', handleMessageSubmit);
                newMessageInput.addEventListener('input', handleTyping);
                newMessageInput.addEventListener('keydown', handleEnterKey);
                newMessageInput.addEventListener('keypress', handleEnterKeyPress);
                updateTextDirection(newMessageInput, true);
            }
        }

        // آپدیت دکمه‌ها تو block-button-container
        const blockButtonContainer = document.getElementById('block-button-container');
        if (blockButtonContainer) {
            blockButtonContainer.innerHTML = `
                <button id="block-button" class="text-sm bg-gray-500 text-white px-3 py-1 rounded hover:bg-gray-600 ${isBlockedByMe ? 'hidden' : ''}">
                    بلاک
                </button>
                <button id="unblock-button" class="text-sm bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600 ${isBlockedByMe ? '' : 'hidden'}">
                    آنبلاک
                </button>
            `;
            const newBlockButton = document.getElementById('block-button');
            const newUnblockButton = document.getElementById('unblock-button');

            if (newBlockButton) {
                newBlockButton.addEventListener('click', function() {
                    confirmBlock(username);
                });
            } else {
                console.warn("دکمه بلاک بعد از آپدیت UI پیدا نشد.");
            }

            if (newUnblockButton) {
                newUnblockButton.addEventListener('click', function() {
                    confirmUnblock(username);
                });
            } else {
                console.warn("دکمه آنبلاک بعد از آپدیت UI پیدا نشد.");
            }
        } else {
            console.warn("کانتینر دکمه‌ها (block-button-container) پیدا نشد، دکمه‌ها به DOM اضافه نمی‌شوند.");
        }
    }

    // توابع برای بلاک و آنبلاک
    function confirmBlock(username) {
        const confirmBlock = confirm(`آیا مطمئنید که می‌خواهید ${username} را بلاک کنید؟`);
        if (confirmBlock) {
            blockUser(username);
            // ارسال پیام WebSocket برای بلاک
            if (chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(JSON.stringify({
                    'type': 'block_message',
                    'action': 'block'
                }));
            }
        }
    }

    function confirmUnblock(username) {
        console.log("نمایش پیام تایید برای آنبلاک کردن", username);
        const confirmUnblock = confirm(`آیا مطمئنید که می‌خواهید ${username} را از بلاک خارج کنید؟`);
        if (confirmUnblock) {
            console.log("کاربر تایید کرد، ارسال درخواست آنبلاک...");
            unblockUser(username);
            // ارسال پیام WebSocket برای آنبلاک
            if (chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(JSON.stringify({
                    'type': 'block_message',
                    'action': 'unblock'
                }));
            }
        } else {
            console.log("کاربر آنبلاک را لغو کرد.");
        }
    }

    function blockUser(username) {
        console.log("در حال ارسال درخواست بلاک برای:", username);
        fetch(`/block_user/${username}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
        })
        .then(response => {
            console.log("پاسخ سرور برای بلاک:", response);
            return response.json();
        })
        .then(data => {
            console.log("داده دریافت‌شده برای بلاک:", data);
            if (data.status === "success") {
                console.log("کاربر با موفقیت بلاک شد");
            } else {
                console.error("خطا در بلاک کردن:", data.error);
            }
        })
        .catch(error => console.error("خطا:", error));
    }

    function unblockUser(username) {
        console.log("در حال ارسال درخواست آنبلاک برای:", username);
        fetch(`/unblock_user/${username}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
        })
        .then(response => {
            console.log("پاسخ سرور برای آنبلاک:", response);
            console.log("وضعیت پاسخ:", response.status);
            if (!response.ok) {
                throw new Error(`خطای HTTP! وضعیت: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("داده دریافت‌شده برای آنبلاک:", data);
            if (data.status === "success") {
                console.log("کاربر با موفقیت آنبلاک شد");
            } else {
                console.error("خطا در آنبلاک کردن:", data.error);
            }
        })
        .catch(error => console.error("خطا:", error));
    }

    // تابع برای ارسال پیام
    function handleMessageSubmit(e) {
        e.preventDefault();
        const messageInput = document.getElementById('message-input'); // دوباره از DOM می‌گیرم
        if (messageInput) {
            const message = messageInput.value.trim();
            if (message) {
                if (chatSocket.readyState === WebSocket.OPEN) {
                    chatSocket.send(JSON.stringify({
                        'type': 'chat_message',
                        'message': message
                    }));
                } else {
                    console.error("WebSocket باز نیست. لطفاً صفحه را رفرش کنید.");
                }
                messageInput.value = '';
                updateTextDirection(messageInput, true);
            }
        }
    }

    // تابع برای مدیریت تایپینگ
    function handleTyping() {
        const text = this.value;
        const isPersian = detectLanguage(text);
        updateTextDirection(this, isPersian);

        clearTimeout(typingTimeout);
        if (chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                'type': 'typing',
                'is_typing': true
            }));
        }
        typingTimeout = setTimeout(() => {
            if (chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(JSON.stringify({
                    'type': 'typing',
                    'is_typing': false
                }));
            }
        }, 1000);
    }

    // توابع برای مدیریت Enter
    function handleEnterKey(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
        }
    }

    function handleEnterKeyPress(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
        }
    }

    // تابع برای اسکرول به پایین
    function scrollToBottom() {
        setTimeout(() => {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }, 0);
    }

    // تابع برای آپدیت جهت متن
    function updateTextDirection(element, isPersian) {
        if (isPersian) {
            element.style.direction = 'rtl';
            element.style.textAlign = 'right';
            element.style.unicodeBidi = 'embed';
        } else {
            element.style.direction = 'ltr';
            element.style.textAlign = 'left';
            element.style.unicodeBidi = 'isolate';
        }
    }

    // تشخیص زبان
    function detectLanguage(text) {
        if (!text) return true;
        const cleanText = text.replace(/[\s.,!?؟!()[\]{}<>،؛:]/g, '');
        if (!cleanText) return true;
        let persianCount = 0;
        let latinCount = 0;
        for (let char of cleanText) {
            const charCode = char.charCodeAt(0);
            if (charCode >= 0x0600 && charCode <= 0x06FF) {
                persianCount++;
            } else if ((charCode >= 0x0041 && charCode <= 0x005A) || (charCode >= 0x0061 && charCode <= 0x007A)) {
                latinCount++;
            }
        }
        return persianCount >= latinCount;
    }

    // فرمت کردن زمان آخرین بازدید
    function formatLastSeen(timestamp) {
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diff = (now - date) / 1000; // تفاوت به ثانیه
        if (diff < 60) return "چند لحظه پیش";
        if (diff < 3600) return Math.floor(diff / 60) + " دقیقه پیش";
        if (diff < 86400) return Math.floor(diff / 3600) + " ساعت پیش";
        return date.toLocaleString('fa-IR', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' });
    }

    // تابع برای آپدیت زمان "چند لحظه پیش" هر ۵ دقیقه
    function startLastSeenUpdate() {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
        updateInterval = setInterval(() => {
            if (lastSeenTimestamp && !userStatusIndicator.classList.contains("online")) {
                userStatusText.textContent = formatLastSeen(lastSeenTimestamp);
            }
        }, 5 * 60 * 1000); // هر ۵ دقیقه
    }

    // تابع برای حذف وضعیت "ارسال شد" یا "دیده شد" از تمام پیام‌های ارسالی
    function clearAllMessageStatuses() {
        const sentMessages = messagesDiv.querySelectorAll('.message');
        sentMessages.forEach(message => {
            if (message.querySelector('.bubble').classList.contains('bg-purple-800')) { // پیام‌های ارسالی
                const statusText = message.querySelector('.status-text');
                if (statusText) {
                    statusText.textContent = '';
                }
            }
        });
    }

    // تابع برای آپدیت وضعیت "دیده شد" یا "ارسال شد" فقط برای آخرین پیام ارسالی
    function updateMessageStatus(messageId) {
        clearAllMessageStatuses();
        const message = messagesDiv.querySelector(`.message[data-message-id="${messageId}"]`);
        if (!message) {
            console.log(`پیام با message_id: ${messageId} در DOM پیدا نشد`);
            return;
        }
        const isSentMessage = message.querySelector('.bubble').classList.contains('bg-purple-800');
        if (!isSentMessage) {
            console.log(`پیام ${messageId} متعلق به کاربر فعلی نیست، وضعیت نمایش داده نمی‌شود`);
            return;
        }
        const isRead = message.dataset.isRead === 'true';
        const statusText = message.querySelector('.status-text');
        if (statusText) {
            if (receiverAlwaysKeepUnread) {
                statusText.textContent = 'ارسال شد';
            } else {
                statusText.textContent = isRead ? 'دیده شد' : 'ارسال شد';
            }
        }
    }

    // گرفتن تنظیمات کاربر مقابل (گیرنده)
    async function fetchReceiverSettings() {
        try {
            const response = await fetch(`/get_user_settings/${username}/`);
            const data = await response.json();
            receiverAlwaysKeepUnread = data.always_keep_unread;
            console.log(`تنظیم always_keep_unread برای گیرنده ${username}: ${receiverAlwaysKeepUnread}`);
            const sentMessages = Array.from(document.querySelectorAll('.message')).filter(message =>
                message.querySelector('.bubble').classList.contains('bg-purple-800')
            );
            if (sentMessages.length > 0) {
                const lastSentMessage = sentMessages[sentMessages.length - 1];
                updateMessageStatus(lastSentMessage.dataset.messageId);
            }
        } catch (error) {
            console.error("خطا در گرفتن تنظیمات کاربر:", error);
        }
    }

    fetchReceiverSettings();

    // متغیر برای مدیریت بازاتصال
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectInterval = 3000; // 3 ثانیه

    // تابع برای اتصال به WebSocket چت
    function connectChatSocket() {
        const chatSocket = new WebSocket(
            `ws://${window.location.host}/ws/chat/${username}/`
        );

        chatSocket.onopen = function() {
            console.log("اتصال به WebSocket چت برقرار شد");
            reconnectAttempts = 0;
            chatSocket.send(JSON.stringify({
                'type': 'chat_opened'
            }));
        };

        chatSocket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log("پیام دریافت شد:", data);

            if (data.type === "chat_message") {
                if (document.body.dataset.isBlocked === "true") {
                    console.log("پیام جدید دریافت شد اما به دلیل بلاک نمایش داده نمی‌شود");
                    return;
                }

                const messageDiv = document.createElement('div');
                messageDiv.className = `message mb-4 flex flex-col ${
                    data.sender === currentUser ? 'items-start' : 'items-end'
                }`;
                messageDiv.dataset.messageId = data.message_id || '';
                messageDiv.dataset.isRead = data.is_read ? 'true' : 'false';
                messageDiv.dataset.receiverAlwaysKeepUnread = data.receiver_always_keep_unread ? 'true' : 'false';

                const bubbleDiv = document.createElement('div');
                bubbleDiv.className = `bubble max-w-xs p-3 rounded-2xl text-sm shadow-md ${
                    data.sender === currentUser
                        ? 'bg-purple-800 text-white rounded-br-md rounded-bl-2xl'
                        : 'bg-white text-gray-800 rounded-bl-md rounded-br-2xl'
                }`;
                bubbleDiv.textContent = data.text;

                const isPersian = detectLanguage(data.text);
                updateTextDirection(bubbleDiv, isPersian);

                messageDiv.appendChild(bubbleDiv);

                const timeDiv = document.createElement('div');
                timeDiv.className = `time flex gap-1 mt-1 text-xs text-gray-500 ${
                    data.sender === currentUser ? 'justify-start' : 'justify-end'
                }`;

                const timeText = document.createElement('span');
                timeText.className = 'time-text';
                timeText.textContent = data.created_at ? data.created_at : new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
                timeDiv.appendChild(timeText);

                if (data.sender === currentUser) {
                    const statusText = document.createElement('span');
                    statusText.className = 'status-text';
                    if (data.receiver_always_keep_unread) {
                        statusText.textContent = 'ارسال شد';
                    } else {
                        statusText.textContent = data.is_read ? 'دیده شد' : 'ارسال شد';
                    }
                    timeDiv.appendChild(statusText);
                }

                messageDiv.appendChild(timeDiv);
                messagesDiv.appendChild(messageDiv);
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
                    clearAllMessageStatuses();
                }

                if (data.sender === currentUser) {
                    updateMessageStatus(data.message_id);
                }
            } else if (data.type === "block_status") {
                const isBlockedByMe = data.blocker_username === currentUser && data.action === 'block';
                const isUnblockedByMe = data.blocker_username === currentUser && data.action === 'unblock';
                const isBlockedByOther = data.blocked_username === currentUser && data.action === 'block';
                const isUnblockedByOther = data.blocked_username === currentUser && data.action === 'unblock';
                const isBlocked = (isBlockedByMe || isBlockedByOther) && !isUnblockedByMe && !isUnblockedByOther;

                // آپدیت UI برای هر دو حالت (بلاک‌کننده و بلاک‌شده)
                updateBlockUI(isBlocked, isBlockedByMe, isBlockedByOther);
            } else if (data.type === "typing") {
                if (data.username === username) {
                    if (data.is_typing) {
                        typingIndicator.classList.add("active");
                        typingIndicator.style.opacity = '1';
                    } else {
                        typingIndicator.classList.remove("active");
                        typingIndicator.style.opacity = '0';
                    }
                }
            } else if (data.type === "chat_opened") {
                if (data.username === username) {
                    receiverAlwaysKeepUnread = data.always_keep_unread;
                    if (data.always_keep_unread) {
                        console.log("گیرنده always_keep_unread فعال دارد، وضعیت پیام‌ها تغییر نمی‌کند");
                        const sentMessages = Array.from(document.querySelectorAll('.message')).filter(message =>
                            message.querySelector('.bubble').classList.contains('bg-purple-800')
                        );
                        if (sentMessages.length > 0) {
                            const lastSentMessage = sentMessages[sentMessages.length - 1];
                            updateMessageStatus(lastSentMessage.dataset.messageId);
                        }
                        return;
                    }

                    const sentMessages = messagesDiv.querySelectorAll('.message[data-is-read="false"]');
                    sentMessages.forEach(message => {
                        if (message.querySelector('.bubble').classList.contains('bg-purple-800')) {
                            message.dataset.isRead = 'true';
                            updateMessageStatus(message.dataset.messageId);
                        }
                    });
                }
            } else if (data.type === "settings_updated") {
                if (data.username === username) {
                    receiverAlwaysKeepUnread = data.always_keep_unread;
                    const sentMessages = Array.from(document.querySelectorAll('.message')).filter(message =>
                        message.querySelector('.bubble').classList.contains('bg-purple-800')
                    );
                    if (sentMessages.length > 0) {
                        const lastSentMessage = sentMessages[sentMessages.length - 1];
                        updateMessageStatus(lastSentMessage.dataset.messageId);
                    }
                }
            }
        };

        chatSocket.onclose = function(event) {
            console.log("اتصال WebSocket بسته شد:", event);
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`تلاش برای بازاتصال (${reconnectAttempts}/${maxReconnectAttempts})...`);
                setTimeout(connectChatSocket, reconnectInterval);
            } else {
                console.error("حداکثر تعداد تلاش‌ها برای بازاتصال به پایان رسید. لطفاً صفحه را رفرش کنید.");
            }
        };

        return chatSocket;
    }

    // اتصال اولیه به WebSocket چت
    let chatSocket = connectChatSocket();

    // WebSocket برای وضعیت کاربر
    const userStatusSocket = new WebSocket(
        `ws://${window.location.host}/ws/user_status/`
    );

    userStatusSocket.onopen = function() {
        console.log("اتصال به WebSocket وضعیت برقرار شد");
    };

    userStatusSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === "user_status" && data.username === username) {
            fetch(`/get_user_status/${username}/`)
                .then(response => response.json())
                .then(statusData => {
                    const isBlocked = document.body.dataset.isBlocked === "true";
                    if (isBlocked) {
                        userStatusText.textContent = "چند لحظه پیش";
                        userStatusIndicator.classList.add("offline");
                        userStatusIndicator.classList.remove("online");
                        userStatusDot.classList.add("offline");
                        userStatusDot.classList.remove("online");
                        if (updateInterval) {
                            clearInterval(updateInterval);
                        }
                        return;
                    }
                    if (statusData.hide_online_status) {
                        userStatusText.textContent = '';
                        userStatusIndicator.classList.remove("online", "offline");
                        userStatusDot.classList.remove("online", "offline");
                    } else if (statusData.is_online) {
                        userStatusText.textContent = 'آنلاین';
                        userStatusIndicator.classList.add("online");
                        userStatusIndicator.classList.remove("offline");
                        userStatusDot.classList.add("online");
                        userStatusDot.classList.remove("offline");
                        if (updateInterval) {
                            clearInterval(updateInterval);
                        }
                    } else {
                        lastSeenTimestamp = statusData.last_seen;
                        userStatusText.textContent = formatLastSeen(lastSeenTimestamp);
                        userStatusIndicator.classList.add("offline");
                        userStatusIndicator.classList.remove("online");
                        userStatusDot.classList.add("offline");
                        userStatusDot.classList.remove("online");
                        startLastSeenUpdate();
                    }
                })
                .catch(error => console.error("خطا در به‌روزرسانی وضعیت کاربر:", error));
        }
    };

    userStatusSocket.onclose = function(event) {
        console.log("اتصال WebSocket وضعیت بسته شد:", event);
    };

    // گرفتن وضعیت اولیه کاربر
    fetch(`/get_user_status/${username}/`)
        .then(response => response.json())
        .then(data => {
            if (data.hide_online_status) {
                userStatusText.textContent = '';
                userStatusIndicator.classList.remove("online", "offline");
                userStatusDot.classList.remove("online", "offline");
            } else if (data.is_online) {
                userStatusText.textContent = 'آنلاین';
                userStatusIndicator.classList.add("online");
                userStatusIndicator.classList.remove("offline");
                userStatusDot.classList.add("online");
                userStatusDot.classList.remove("offline");
            } else {
                lastSeenTimestamp = data.last_seen;
                userStatusText.textContent = formatLastSeen(lastSeenTimestamp);
                userStatusIndicator.classList.add("offline");
                userStatusIndicator.classList.remove("online");
                userStatusDot.classList.add("offline");
                userStatusDot.classList.remove("online");
                startLastSeenUpdate();
            }
        })
        .catch(error => console.error("خطا در گرفتن وضعیت کاربر:", error));

    // توابع برای مدیریت پاپ‌آپ‌ها
    function openProfileModal(username) {
        fetch(`/get_user_profile/${username}/`)
            .then(response => response.json())
            .then(data => {
                profileUsername.textContent = data.username;
                profilePhone.textContent = data.phone_number ? `شماره تماس: ${data.phone_number}` : '';
                profileEmail.textContent = data.email ? `ایمیل: ${data.email}` : '';
                profileBio.textContent = data.bio ? `بیو: ${data.bio}` : '';
                profileDateJoined.textContent = data.date_joined ? `تاریخ عضویت: ${data.date_joined}` : '';
                photos = data.photos || [];
                currentPhotoIndex = 0;
                profileMainPhoto.src = data.profile_photo || '/static/default_profile.png';
                profileModal.classList.remove('hidden');
            })
            .catch(error => console.error("خطا در گرفتن اطلاعات پروفایل:", error));
    }

    function closeProfileModal() {
        profileModal.classList.add('hidden');
    }

    function openPhotoModal() {
        if (photos.length > 0) {
            photoModalImage.src = photos[currentPhotoIndex].url;
        } else {
            photoModalImage.src = profileMainPhoto.src;
        }
        photoModal.classList.remove('hidden');
        closeProfileModal();
    }

    function closePhotoModal() {
        photoModal.classList.add('hidden');
    }

    function prevPhoto() {
        if (photos.length > 0) {
            currentPhotoIndex = (currentPhotoIndex - 1 + photos.length) % photos.length;
            photoModalImage.src = photos[currentPhotoIndex].url;
        }
    }

    function nextPhoto() {
        if (photos.length > 0) {
            currentPhotoIndex = (currentPhotoIndex + 1) % photos.length;
            photoModalImage.src = photos[currentPhotoIndex].url;
        }
    }

    // تنظیم جهت اولیه برای پیام‌های موجود
    document.querySelectorAll('.message .bubble').forEach(bubble => {
        const text = bubble.textContent;
        const isPersian = detectLanguage(text);
        updateTextDirection(bubble, isPersian);
    });

    // تنظیم جهت اولیه برای textarea (اگه وجود داشته باشه)
    if (messageInput) {
        updateTextDirection(messageInput, true);
    }

    // اضافه کردن event listenerها برای دکمه‌های اولیه
    if (blockButton) {
        blockButton.addEventListener('click', function() {
            confirmBlock(username);
        });
    } else {
        console.warn("هشدار: دکمه بلاک پیدا نشد، event listener اضافه نشد.");
    }

    if (unblockButton) {
        unblockButton.addEventListener('click', function() {
            confirmUnblock(username);
        });
    } else {
        console.warn("هشدار: دکمه آنبلاک پیدا نشد، event listener اضافه نشد.");
    }

    // مدیریت فرم اولیه (اگه وجود داشته باشه)
    if (messageForm) {
        messageForm.addEventListener('submit', handleMessageSubmit);
    }
    if (messageInput) {
        messageInput.addEventListener('input', handleTyping);
        messageInput.addEventListener('keydown', handleEnterKey);
        messageInput.addEventListener('keypress', handleEnterKeyPress);
    }

    // تغییر وضعیت آنلاین در صورت بلاک
    if (isBlocked) {
        userStatusIndicator.classList.remove("online");
        userStatusIndicator.classList.add("offline");
        userStatusDot.classList.remove("online");
        userStatusDot.classList.add("offline");
        userStatusText.textContent = "چند لحظه پیش";
    }

    // اسکرول به پایین پیام‌ها هنگام لود صفحه
    scrollToBottom();

    // آپدیت اولیه وضعیت "دیده شد" یا "ارسال شد" برای پیام‌های موجود
    const sentMessages = Array.from(document.querySelectorAll('.message')).filter(message =>
        message.querySelector('.bubble').classList.contains('bg-purple-800')
    );
    if (sentMessages.length > 0) {
        const lastSentMessage = sentMessages[sentMessages.length - 1];
        updateMessageStatus(lastSentMessage.dataset.messageId);
    }

    // اطمینان از اسکرول به پایین بعد از لود کامل DOM و رندر پیام‌ها
    window.addEventListener('load', scrollToBottom);
});