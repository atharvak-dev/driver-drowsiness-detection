const CACHE_NAME = 'drowsiness-detection-v1';
const urlsToCache = [
  '/',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  // Add other static assets that should be cached
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache);
      })
      .catch((error) => {
        console.log('Service Worker: Cache failed', error);
      })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  // Skip cache for streaming requests (Streamlit WebRTC)
  if (event.request.url.includes('webrtc') || 
      event.request.url.includes('ws://') || 
      event.request.url.includes('wss://')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Return cached version or fetch from network
        if (response) {
          return response;
        }
        
        // Validate request URL to prevent SSRF
        const url = new URL(event.request.url);
        const allowedOrigins = [self.location.origin, 'https://apis.mappls.com'];
        
        if (!allowedOrigins.some(origin => url.origin === origin || url.origin.startsWith('http://localhost') || url.origin.startsWith('http://127.0.0.1'))) {
          return new Response('Forbidden', { status: 403 });
        }
        
        return fetch(event.request)
          .catch((error) => {
            console.error('Service Worker: Fetch failed', error);
            // If both cache and network fail, return a custom offline page
            if (event.request.destination === 'document') {
              return caches.match('/offline.html')
                .catch(() => new Response('Offline', { status: 503 }));
            }
            return new Response('Network error', { status: 503 });
          });
      })
      .catch((error) => {
        console.error('Service Worker: Cache match failed', error);
        return new Response('Cache error', { status: 500 });
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Background sync for when connection is restored
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    console.log('Service Worker: Background sync triggered');
    // Handle background sync tasks here
  }
});

// Push notification support (for future features)
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'Drowsiness alert!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Open App',
        icon: '/icons/icon-192x192.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/icons/icon-192x192.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Driver Drowsiness Detection', options)
  );
});
