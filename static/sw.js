const CACHE = 'activityos-v2';
const OFFLINE_URL = '/dashboard';
const ASSETS = ['/dashboard','/tasks','/roadmap','/analytics',
  'https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Outfit:wght@400;600;700;800&display=swap',
  'https://unpkg.com/lucide@latest/dist/umd/lucide.min.js'];

// Install & cache
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS).catch(()=>{}))
  );
  self.skipWaiting();
});

// Activate & clean old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

// Fetch — network first, fallback to cache
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match(OFFLINE_URL)))
  );
});

// Push Notification handler
self.addEventListener('push', e => {
  const data = e.data?.json() || { title:'ActivityOS', body:'Ada notifikasi baru!' };
  e.waitUntil(
    self.registration.showNotification(data.title, {
      body:  data.body,
      icon:  '/static/icons/icon-192.png',
      badge: '/static/icons/badge-72.png',
      vibrate: [200, 100, 200],
      data: { url: data.url || '/dashboard' },
      actions: [
        { action:'open',    title:'Buka App' },
        { action:'dismiss', title:'Tutup' }
      ]
    })
  );
});

// Notification click
self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'dismiss') return;
  const url = e.notification.data?.url || '/dashboard';
  e.waitUntil(
    clients.matchAll({type:'window'}).then(list => {
      const existing = list.find(c => c.url.includes(url) && 'focus' in c);
      if (existing) return existing.focus();
      return clients.openWindow(url);
    })
  );
});

// ── SCHEDULED REMINDERS ──
// ISQ Morning reminder at 7:00 AM
// ISQ Evening reminder at 8:30 PM
self.addEventListener('periodicsync', e => {
  if (e.tag === 'isq-morning') {
    e.waitUntil(self.registration.showNotification('🌅 Ritual Pagi ISQ', {
      body: 'Belum isi ritual pagi hari ini. Set intention & gratitude kamu yuk!',
      icon: '/static/icons/icon-192.png',
      badge:'/static/icons/badge-72.png',
      data: { url: '/isq' },
      vibrate: [200,100,200]
    }));
  }
  if (e.tag === 'isq-evening') {
    e.waitUntil(self.registration.showNotification('🌙 Refleksi Malam ISQ', {
      body: 'Hari hampir selesai. Luangkan 3 menit untuk refleksi malammu.',
      icon: '/static/icons/icon-192.png',
      badge:'/static/icons/badge-72.png',
      data: { url: '/isq' },
      vibrate: [200,100,200,100,200]
    }));
  }
});
