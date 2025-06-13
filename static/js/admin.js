// 图床管理后台 - 优化重构版
class AdminPanel {
    constructor() {
        this.state = {
            isLoggedIn: false,
            username: '',
            currentPage: 1,
            pageSize: 20,
            totalPages: 1,
            selectedIds: new Set(),
            images: [],
            searchQuery: '',
            theme: localStorage.getItem('theme') || 'light'
        };

        this.init();
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.applyTheme();
        this.checkAuth();
    }

    cacheElements() {
        this.elements = {
            // 容器
            loginContainer: document.getElementById('loginContainer'),
            adminPanel: document.getElementById('adminPanel'),
            
            // 登录表单
            loginForm: document.getElementById('loginForm'),
            username: document.getElementById('username'),
            password: document.getElementById('password'),
            
            // 导航栏
            adminUser: document.getElementById('adminUser'),
            settingsBtn: document.getElementById('settingsBtn'),
            logoutBtn: document.getElementById('logoutBtn'),
            themeToggle: document.getElementById('themeToggle'),
            
            // 统计
            totalImages: document.getElementById('totalImages'),
            totalSize: document.getElementById('totalSize'),
            todayUploads: document.getElementById('todayUploads'),
            selectedCount: document.getElementById('selectedCount'),
            
            // 操作栏
            selectAll: document.getElementById('selectAll'),
            deleteSelectedBtn: document.getElementById('deleteSelectedBtn'),
            deleteCount: document.getElementById('deleteCount'),
            searchInput: document.getElementById('searchInput'),
            refreshBtn: document.getElementById('refreshBtn'),
            clearCacheBtn: document.getElementById('clearCacheBtn'),
            
            // 图片列表
            imageList: document.getElementById('imageList'),
            pagination: document.getElementById('pagination'),
            
            // 模态框
            deleteModal: document.getElementById('deleteModal'),
            deleteMessage: document.getElementById('deleteMessage'),
            cancelDeleteBtn: document.getElementById('cancelDeleteBtn'),
            confirmDeleteBtn: document.getElementById('confirmDeleteBtn'),
            
            settingsModal: document.getElementById('settingsModal'),
            settingsForm: document.getElementById('settingsForm'),
            newUsername: document.getElementById('newUsername'),
            newPassword: document.getElementById('newPassword'),
            confirmPassword: document.getElementById('confirmPassword'),
            cancelSettingsBtn: document.getElementById('cancelSettingsBtn'),
            
            // Toast
            toastContainer: document.getElementById('toastContainer')
        };
    }

    setupEventListeners() {
        // 登录表单提交
        this.elements.loginForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // 退出登录
        this.elements.logoutBtn?.addEventListener('click', () => {
            this.handleLogout();
        });

        // 主题切换
        this.elements.themeToggle?.addEventListener('click', () => {
            this.toggleTheme();
        });

        // 设置按钮
        this.elements.settingsBtn?.addEventListener('click', () => {
            this.showSettings();
        });

        // 设置表单提交
        this.elements.settingsForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleUpdateCredentials();
        });

        // 取消设置
        this.elements.cancelSettingsBtn?.addEventListener('click', () => {
            this.hideSettings();
        });

        // 全选
        this.elements.selectAll?.addEventListener('change', (e) => {
            this.handleSelectAll(e.target.checked);
        });

        // 删除选中
        this.elements.deleteSelectedBtn?.addEventListener('click', () => {
            this.showDeleteConfirm();
        });

        // 搜索
        let searchTimer;
        this.elements.searchInput?.addEventListener('input', (e) => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                this.state.searchQuery = e.target.value;
                this.state.currentPage = 1;
                this.loadImages();
            }, 300);
        });

        // 刷新
        this.elements.refreshBtn?.addEventListener('click', () => {
            this.loadImages();
            this.loadStats();
        });

        // 清理缓存
        this.elements.clearCacheBtn?.addEventListener('click', () => {
            this.handleClearCache();
        });

        // 删除确认模态框
        this.elements.cancelDeleteBtn?.addEventListener('click', () => {
            this.hideDeleteConfirm();
        });

        this.elements.confirmDeleteBtn?.addEventListener('click', () => {
            this.handleDeleteConfirm();
        });

        // 点击模态框外部关闭
        this.elements.deleteModal?.addEventListener('click', (e) => {
            if (e.target === this.elements.deleteModal) {
                this.hideDeleteConfirm();
            }
        });

        this.elements.settingsModal?.addEventListener('click', (e) => {
            if (e.target === this.elements.settingsModal) {
                this.hideSettings();
            }
        });
    }

    // 主题管理
    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.state.theme);
    }

    toggleTheme() {
        this.state.theme = this.state.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', this.state.theme);
        this.applyTheme();
    }

    // 认证相关
    async checkAuth() {
        try {
            const response = await fetch('/api/admin/check', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                if (data.authenticated) {
                    this.showAdminPanel(data.username);
                    return;
                }
            }
        } catch (error) {
            console.error('Auth check failed:', error);
        }

        this.showLoginForm();
    }

    async handleLogin() {
        const username = this.elements.username.value.trim();
        const password = this.elements.password.value;

        if (!username || !password) {
            this.showToast('请填写用户名和密码', 'error');
            return;
        }

        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password }),
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showToast('登录成功', 'success');
                this.showAdminPanel(data.username || username);
            } else {
                this.showToast(data.error || '登录失败', 'error');
                this.elements.password.value = '';
                this.elements.password.focus();
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showToast('登录失败，请稍后重试', 'error');
        }
    }

    async handleLogout() {
        try {
            await fetch('/api/admin/logout', {
                method: 'POST',
                credentials: 'include'
            });
            
            this.showToast('已退出登录', 'info');
            this.showLoginForm();
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    showLoginForm() {
        this.state.isLoggedIn = false;
        this.elements.loginContainer.style.display = 'flex';
        this.elements.adminPanel.style.display = 'none';
        this.elements.settingsBtn.style.display = 'none';
        this.elements.logoutBtn.style.display = 'none';
        this.elements.username.focus();
    }

    showAdminPanel(username) {
        this.state.isLoggedIn = true;
        this.state.username = username;
        this.elements.loginContainer.style.display = 'none';
        this.elements.adminPanel.style.display = 'block';
        this.elements.adminUser.textContent = `管理员: ${username}`;
        this.elements.settingsBtn.style.display = 'inline-flex';
        this.elements.logoutBtn.style.display = 'inline-flex';
        
        // 加载数据
        this.loadStats();
        this.loadImages();
    }

    // 数据加载
    async loadStats() {
        try {
            const response = await fetch('/api/admin/stats', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.updateStats(data);
            }
        } catch (error) {
            console.error('Load stats error:', error);
        }
    }

    updateStats(stats) {
        if (this.elements.totalImages) {
            this.elements.totalImages.textContent = stats.total_files || '0';
        }
        
        if (this.elements.totalSize) {
            this.elements.totalSize.textContent = this.formatBytes(stats.total_size || 0);
        }
        
        if (this.elements.todayUploads) {
            this.elements.todayUploads.textContent = stats.today_uploads || '0';
        }
    }

    async loadImages(page = 1) {
        this.state.currentPage = page;
        this.showLoading();

        try {
            const params = new URLSearchParams({
                page: page,
                limit: this.state.pageSize
            });

            if (this.state.searchQuery) {
                params.append('search', this.state.searchQuery);
            }

            const response = await fetch(`/api/admin/images?${params}`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.state.images = data.images || [];
                this.state.totalPages = data.total_pages || 1;
                this.renderImages();
                this.renderPagination();
            } else if (response.status === 401) {
                this.showLoginForm();
            }
        } catch (error) {
            console.error('Load images error:', error);
            this.showToast('加载图片失败', 'error');
        }
    }

    showLoading() {
        this.elements.imageList.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>加载中...</p>
            </div>
        `;
    }

    renderImages() {
        if (this.state.images.length === 0) {
            this.elements.imageList.innerHTML = `
                <div class="empty-state">
                    <p>暂无图片</p>
                </div>
            `;
            return;
        }

        const html = this.state.images.map(image => {
            // CDN缓存标识
            let cdnBadge = '';
            if (image.cdn_cached) {
                cdnBadge = '<span class="cdn-badge">CDN已缓存</span>';
            }
            
            return `
            <div class="image-item" data-id="${image.encrypted_id}">
                <div class="image-checkbox">
                    <input type="checkbox" id="img-${image.encrypted_id}" 
                           ${this.state.selectedIds.has(image.encrypted_id) ? 'checked' : ''}>
                </div>
                <div class="image-preview">
                    <img src="/image/${image.encrypted_id}" alt="${image.original_filename || '图片'}" 
                         loading="lazy" 
                         onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22%3E%3Crect width=%22100%22 height=%22100%22 fill=%22%23ddd%22/%3E%3Ctext x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22%3E加载失败%3C/text%3E%3C/svg%3E';">
                    ${cdnBadge}
                </div>
                <div class="image-info">
                    <div class="image-filename" title="${image.original_filename || '未命名'}">${image.original_filename || '未命名'}</div>
                    <div class="image-meta">
                        <span class="meta-item">
                            <span class="meta-icon">📏</span>${this.formatBytes(image.file_size)}
                        </span>
                        <span class="meta-item">
                            <span class="meta-icon">📍</span>${this.translateSource(image.source)}
                        </span>
                        <span class="meta-item">
                            <span class="meta-icon">🕒</span>${this.formatDate(image.created_at)}
                        </span>
                        <span class="meta-item">
                            <span class="meta-icon">👤</span>${image.username || '未知'}
                        </span>
                    </div>
                    
                    <div class="image-actions">
                        <a href="/image/${image.encrypted_id}" target="_blank" class="btn-link">
                            查看
                        </a>
                        <button class="btn-link btn-copy" data-url="/image/${image.encrypted_id}">
                            复制链接
                        </button>
                        <button class="btn-link btn-delete" data-id="${image.encrypted_id}">
                            删除
                        </button>
                    </div>
                </div>
            </div>
        `}).join('');

        this.elements.imageList.innerHTML = html;
        this.bindImageEvents();
    }

    translateSource(source) {
        const sourceMap = {
            'telegram_bot': 'Telegram机器人',
            'web_upload': 'Web上传',
            'api': 'API上传'
        };
        return sourceMap[source] || source;
    }

    bindImageEvents() {
        // 复选框事件
        const checkboxes = this.elements.imageList.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const imageId = e.target.closest('.image-item').dataset.id;
                if (e.target.checked) {
                    this.state.selectedIds.add(imageId);
                } else {
                    this.state.selectedIds.delete(imageId);
                }
                this.updateSelectionState();
            });
        });

        // 单个删除按钮
        const deleteButtons = this.elements.imageList.querySelectorAll('.btn-delete');
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const imageId = e.target.dataset.id;
                this.state.selectedIds.clear();
                this.state.selectedIds.add(imageId);
                this.showDeleteConfirm();
            });
        });

        // 复制链接按钮
        const copyButtons = this.elements.imageList.querySelectorAll('.btn-copy');
        copyButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const url = window.location.origin + e.target.dataset.url;
                this.copyToClipboard(url);
            });
        });
    }

    renderPagination() {
        if (this.state.totalPages <= 1) {
            this.elements.pagination.innerHTML = '';
            return;
        }

        const pages = [];
        const current = this.state.currentPage;
        const total = this.state.totalPages;

        // 上一页
        pages.push(`
            <button class="page-btn ${current === 1 ? 'disabled' : ''}" 
                    data-page="${current - 1}" ${current === 1 ? 'disabled' : ''}>
                上一页
            </button>
        `);

        // 页码
        for (let i = 1; i <= total; i++) {
            if (i === 1 || i === total || (i >= current - 2 && i <= current + 2)) {
                pages.push(`
                    <button class="page-btn ${i === current ? 'active' : ''}" 
                            data-page="${i}">${i}</button>
                `);
            } else if (i === current - 3 || i === current + 3) {
                pages.push('<span class="page-ellipsis">...</span>');
            }
        }

        // 下一页
        pages.push(`
            <button class="page-btn ${current === total ? 'disabled' : ''}" 
                    data-page="${current + 1}" ${current === total ? 'disabled' : ''}>
                下一页
            </button>
        `);

        this.elements.pagination.innerHTML = pages.join('');

        // 绑定分页事件
        const pageButtons = this.elements.pagination.querySelectorAll('.page-btn:not(.disabled)');
        pageButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const page = parseInt(e.target.dataset.page);
                this.loadImages(page);
            });
        });
    }

    // 选择操作
    handleSelectAll(checked) {
        const checkboxes = this.elements.imageList.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
            const imageId = checkbox.closest('.image-item').dataset.id;
            if (checked) {
                this.state.selectedIds.add(imageId);
            } else {
                this.state.selectedIds.delete(imageId);
            }
        });
        this.updateSelectionState();
    }

    updateSelectionState() {
        const count = this.state.selectedIds.size;
        this.elements.selectedCount.textContent = count;
        this.elements.deleteCount.textContent = count;
        this.elements.deleteSelectedBtn.disabled = count === 0;
        
        // 更新全选状态
        const totalCheckboxes = this.elements.imageList.querySelectorAll('input[type="checkbox"]').length;
        this.elements.selectAll.checked = count > 0 && count === totalCheckboxes;
        this.elements.selectAll.indeterminate = count > 0 && count < totalCheckboxes;
    }

    // 删除操作
    showDeleteConfirm() {
        const count = this.state.selectedIds.size;
        if (count === 0) return;

        this.elements.deleteMessage.textContent = 
            `确定要删除选中的 ${count} 张图片吗？此操作不可恢复。`;
        this.elements.deleteModal.classList.add('show');
    }

    hideDeleteConfirm() {
        this.elements.deleteModal.classList.remove('show');
    }

    async handleDeleteConfirm() {
        const ids = Array.from(this.state.selectedIds);
        this.hideDeleteConfirm();
        
        try {
            const response = await fetch('/api/admin/images/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ids }),
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showToast(`成功删除 ${data.deleted} 张图片`, 'success');
                this.state.selectedIds.clear();
                this.updateSelectionState();
                this.loadStats();
                this.loadImages(this.state.currentPage);
            } else {
                this.showToast(data.error || '删除失败', 'error');
            }
        } catch (error) {
            console.error('Delete error:', error);
            this.showToast('删除失败，请稍后重试', 'error');
        }
    }

    // 设置功能
    showSettings() {
        this.elements.settingsModal.classList.add('show');
        this.elements.settingsForm.reset();
    }

    hideSettings() {
        this.elements.settingsModal.classList.remove('show');
    }

    async handleUpdateCredentials() {
        const newUsername = this.elements.newUsername.value.trim();
        const newPassword = this.elements.newPassword.value;
        const confirmPassword = this.elements.confirmPassword.value;

        if (!newUsername && !newPassword) {
            this.showToast('请至少填写新用户名或新密码', 'error');
            return;
        }

        if (newPassword && newPassword !== confirmPassword) {
            this.showToast('两次输入的密码不一致', 'error');
            return;
        }

        try {
            const response = await fetch('/api/admin/update_credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: newUsername || null,
                    password: newPassword || null
                }),
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showToast(data.message || '凭据更新成功', 'success');
                
                if (data.updated_username && newUsername) {
                    this.elements.adminUser.textContent = `管理员: ${newUsername}`;
                }
                
                this.hideSettings();
                
                if (data.updated_password) {
                    setTimeout(() => {
                        this.showToast('密码已更新，请重新登录', 'info');
                        setTimeout(() => {
                            this.handleLogout();
                        }, 2000);
                    }, 1000);
                }
            } else {
                this.showToast(data.error || '更新失败', 'error');
            }
        } catch (error) {
            console.error('Update credentials error:', error);
            this.showToast('更新失败，请稍后重试', 'error');
        }
    }

    // 清理缓存
    async handleClearCache() {
        if (!confirm('确定要清理CDN缓存吗？这将强制所有客户端重新加载资源。')) {
            return;
        }
        
        try {
            const response = await fetch('/api/admin/clear_cache', {
                method: 'POST',
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.showToast('缓存已清理！页面将自动刷新', 'success');
                
                // 清理Service Worker缓存
                if ('caches' in window) {
                    const cacheNames = await caches.keys();
                    await Promise.all(
                        cacheNames.map(cacheName => caches.delete(cacheName))
                    );
                }
                
                // 2秒后刷新页面
                setTimeout(() => {
                    window.location.reload(true);
                }, 2000);
            } else {
                this.showToast(data.error || '清理缓存失败', 'error');
            }
        } catch (error) {
            console.error('Clear cache error:', error);
            this.showToast('清理缓存失败', 'error');
        }
    }

    // 工具函数
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        if (!dateString) return '未知时间';
        
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return '未知时间';
            
            const now = new Date();
            const diff = now - date;
            
            if (diff < 0) return '刚刚';
            if (diff < 60000) return '刚刚';
            if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
            if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
            if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
            
            return date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } catch (error) {
            return '未知时间';
        }
    }

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('链接已复制', 'success');
        } catch (err) {
            // 降级方案
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            this.showToast('链接已复制', 'success');
        }
    }

    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const iconMap = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span class="toast-icon">${iconMap[type]}</span>
            <span class="toast-message">${message}</span>
        `;
        
        this.elements.toastContainer.appendChild(toast);
        
        // 触发重排
        toast.offsetHeight;
        
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// 初始化管理面板
document.addEventListener('DOMContentLoaded', () => {
    new AdminPanel();
});