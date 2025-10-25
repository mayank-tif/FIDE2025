// firebase-messaging-sw.js
try {
  importScripts('https://www.gstatic.com/firebasejs/9.22.2/firebase-app-compat.js');
  importScripts('https://www.gstatic.com/firebasejs/9.22.2/firebase-messaging-compat.js');

  console.log('[Service Worker] Scripts imported successfully');

  // Initialize Firebase
  firebase.initializeApp({
    apiKey: "AIzaSyCVm-LVCLvmc2EGqg_oM8Q-hm2iHKSZfA0",
    authDomain: "fwc2025-6bb44.firebaseapp.com",
    projectId: "fwc2025-6bb44",
    storageBucket: "fwc2025-6bb44.firebasestorage.app",
    messagingSenderId: "939011673539",
    appId: "1:939011673539:web:07c0dad05bbb2a2e0a0176",
    measurementId: "G-YST4RC03W0"
  });

  const messaging = firebase.messaging();
  console.log('[Service Worker] Firebase Messaging initialized');

  messaging.onBackgroundMessage((payload) => {
  console.log('[Service Worker] Background message:', payload);

  // If message contains `notification`, it’s already displayed by Firebase
  // (especially needed for iOS).
  if (payload.notification) {
    console.log('[Service Worker] Skipping showNotification - Firebase will handle it');
    return;
  }

  // Otherwise, it’s a data-only message — handle manually
  const title = payload.data?.title || 'FWC 2025';
  const body = payload.data?.body || 'You have a new notification';

  const baseUrl = self.location.origin;
  const iconUrl = `${baseUrl}/static/assets/images/fide-world-cup-logo.png`;

  return self.registration.showNotification(title, {
    body,
    icon: iconUrl,
    badge: iconUrl,
    data: payload.data,
  });
});


} catch (error) {
  console.error('[Service Worker] Initialization failed:', error);
}

self.addEventListener('notificationclick', (event) => {
  console.log('[Service Worker] Notification clicked');
  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('/') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('/');
      }
    })
  );
});