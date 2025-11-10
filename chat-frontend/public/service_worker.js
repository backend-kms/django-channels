self.addEventListener('push', function(event) {
    const data = event.data ? event.data.json() : {};
    event.waitUntil(
        self.registration.showNotification(data.title || '새 알림', {
            body: data.body || '',
            data: data.url || '/'
        })
    );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data.url;
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(windowClients => {
      for (let client of windowClients) {
        // 절대경로 비교 또는 includes 사용
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        // 절대경로로 열기
        const openUrl = url.startsWith('http') ? url : (self.location.origin + url);
        return clients.openWindow(openUrl);
      }
    })
  );
});