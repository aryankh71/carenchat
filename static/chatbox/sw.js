self.addEventListener('install', function(event) {
    console.log('Service Worker installed');
    event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', function(event) {
    console.log('Service Worker activated');
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function(event) {
    console.log('Service Worker fetching:', event.request.url);
    event.respondWith(fetch(event.request));
});

self.addEventListener('push', function(event) {
    console.log('Push event received:', event);
    const data = event.data ? event.data.json() : { title: 'اعلان تست', body: 'این یک اعلان آزمایشی است!' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/chatbox/img/carenchat-logo.png',
            badge: '/static/chatbox/img/carenchat-logo.png',
            data: data.data
        })
    );
});

self.addEventListener('notificationclick', function(event) {
    console.log('Notification clicked');
    event.notification.close();
    const url = event.notification.data ? event.notification.data.url : '/';
    event.waitUntil(
        clients.openWindow(url)
    );
});
