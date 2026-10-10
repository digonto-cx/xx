// ==========================================================
// MicroEarnX Official PWA Service Worker (v2)
// ==========================================================

const CACHE_NAME = 'microearnx-cache-v2';

// যেসব ফাইল অফলাইনের জন্য প্রাথমিক অবস্থায় ক্যাশ হবে
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/install',
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://i.ibb.co/1JbqCDHq/Add-Text-10-10-03-15-45.jpg'
];

// ১. ইন্সটল ইভেন্ট (ক্যাশিং শুরু)
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// ২. অ্যাক্টিভেট ইভেন্ট (পুরনো ক্যাশ ক্লিয়ার)
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// ৩. ফেচ ইভেন্ট (Network-First Strategy: লাইভ ডাটা অক্ষুণ্ণ রাখা)
self.addEventListener('fetch', (event) => {
    // শুধুমাত্র GET রিকোয়েস্ট ক্যাশ হবে (POST, PUT ইত্যাদি বাইপাস হবে)
    if (event.request.method !== 'GET') {
        return;
    }

    event.respondWith(
        // প্রথমে লাইভ নেটওয়ার্ক থেকে নতুন ডাটা আনার চেষ্টা করবে
        fetch(event.request)
            .then((networkResponse) => {
                // সফল হলে ক্যাশেও আপডেট কপি রেখে দেবে
                if (networkResponse && networkResponse.status === 200) {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                // ইন্টারনেট না থাকলে ক্যাশ থেকে পেজ লোড করবে
                return caches.match(event.request);
            })
    );
});
