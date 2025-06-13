// Service Worker - 优化精简版
const CACHE_VERSION = 'imagebed-v{STATIC_VERSION}';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;
const CDN_DOMAIN = '{CLOUDFLARE_CDN_DOMAIN or ""}';

const STATIC_FILES = [
    '/',
    '/static/js/main.js?v={STATIC_VERSION}',
    '/static/css/styles.css?v={STATIC_VERSION}'
];

// 安装事件
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(STATIC_FILES))
            .then(() => self.skipWaiting())
    );
});

// 激活事件
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name.includes('imagebed-v') && name !== STATIC_CACHE && name !== IMAGE_CACHE)
                    .map(name => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// 请求拦截
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // 只处理GET请求
    if (request.method !== 'GET') return;
    
    // 图片请求处理
    if (url.pathname.startsWith('/image/')) {
        event.respondWith(handleImageRequest(request));
        return;
    }
    
    // 静态资源处理
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(handleStaticRequest(request));
        return;
    }
    
    // API请求 - 网络优先
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request)
                .then(response => {
                    if (response.ok) {
                        const responseToCache = response.clone();
                        caches.open(STATIC_CACHE).then(cache => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return response;
                })
                .catch(() => caches.match(request))
        );
        return;
    }
    
    // 默认策略
    event.respondWith(
        caches.match(request).then(response => response || fetch(request))
    );
});

// 处理图片请求
async function handleImageRequest(request) {
    const cache = await caches.open(IMAGE_CACHE);
    const cached = await cache.match(request);
    
    if (cached) {
        return cached;
    }
    
    try {
        // 如果配置了CDN，尝试从CDN获取
        let fetchUrl = request.url;
        if (CDN_DOMAIN && !request.url.includes(CDN_DOMAIN)) {
            const url = new URL(request.url);
            fetchUrl = `https://${CDN_DOMAIN}${url.pathname}`;
        }
        
        const response = await fetch(fetchUrl);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        // CDN失败，回退到原始URL
        if (fetchUrl !== request.url) {
            return fetch(request);
        }
        throw error;
    }
}

// 处理静态资源请求
async function handleStaticRequest(request) {
    const cached = await caches.match(request);
    
    if (cached) {
        // 检查版本
        const url = new URL(request.url);
        const version = url.searchParams.get('v');
        if (version === '{STATIC_VERSION}') {
            return cached;
        }
    }
    
    // 获取新版本
    const response = await fetch(request);
    if (response.ok) {
        const cache = await caches.open(STATIC_CACHE);
        cache.put(request, response.clone());
    }
    return response;
}

// 监听消息
self.addEventListener('message', event => {
    if (event.data?.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});