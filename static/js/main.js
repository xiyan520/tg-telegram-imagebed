// Telegram 云图床 - 优化精简版 JavaScript (修复图片加载)
class TelegramImageBed {
    constructor() {
        this.state = {
            uploadInProgress: false,
            theme: localStorage.getItem('theme') || 'light',
            stats: {},
            adminLoggedIn: false
        };

        this.config = {
            maxFileSize: 20 * 1024 * 1024, // 20MB
            allowedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml'],
            uploadConcurrency: 3,
            imageLoadTimeout: 30000 // 30秒超时
        };

        this.init();
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.applyTheme();
        this.loadStats();
        this.checkAdminStatus();
        this.startStatsUpdater();
    }

    cacheElements() {
        this.elements = {
            // 主题
            themeToggle: document.getElementById('themeToggle'),
            
            // 上传
            uploadArea: document.getElementById('uploadArea'),
            fileInput: document.getElementById('fileInput'),
            selectBtn: document.getElementById('selectBtn'),
            progressContainer: document.getElementById('progressContainer'),
            progressFill: document.getElementById('progressFill'),
            resultsContainer: document.getElementById('resultsContainer'),
            
            // 统计
            totalFiles: document.getElementById('totalFiles'),
            totalSize: document.getElementById('totalSize'),
            uptime: document.getElementById('uptime'),
            uploadSpeed: document.getElementById('uploadSpeed'),
            cdnCached: document.getElementById('cdnCached'),
            
            // 管理员
            adminStatus: document.getElementById('adminStatus'),
            adminUserDisplay: document.getElementById('adminUserDisplay'),
            adminLogoutBtn: document.getElementById('adminLogoutBtn'),
            
            // Toast
            toastContainer: document.getElementById('toastContainer')
        };
    }

    setupEventListeners() {
        // 主题切换
        this.elements.themeToggle?.addEventListener('click', () => {
            this.setTheme(this.state.theme === 'light' ? 'dark' : 'light');
        });

        // 文件选择
        this.elements.selectBtn?.addEventListener('click', () => {
            this.elements.fileInput.click();
        });

        this.elements.fileInput?.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });

        // 拖拽上传
        this.setupDragAndDrop();

        // 粘贴上传
        document.addEventListener('paste', (e) => {
            const items = Array.from(e.clipboardData.items);
            const files = items
                .filter(item => item.type.startsWith('image/'))
                .map(item => item.getAsFile())
                .filter(Boolean);
            
            if (files.length > 0) {
                this.handleFiles(files);
            }
        });

        // 管理员退出
        this.elements.adminLogoutBtn?.addEventListener('click', () => {
            this.handleAdminLogout();
        });
    }

    setupDragAndDrop() {
        const uploadArea = this.elements.uploadArea;
        if (!uploadArea) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
            uploadArea.addEventListener(event, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(event => {
            uploadArea.addEventListener(event, () => {
                uploadArea.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(event => {
            uploadArea.addEventListener(event, () => {
                uploadArea.classList.remove('dragover');
            });
        });

        uploadArea.addEventListener('drop', (e) => {
            this.handleFiles(e.dataTransfer.files);
        });
    }

    // 主题管理
    setTheme(theme) {
        this.state.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    applyTheme() {
        this.setTheme(this.state.theme);
    }

    // 文件处理
    async handleFiles(fileList) {
        if (this.state.uploadInProgress) {
            this.showToast('正在上传中，请稍候...', 'warning');
            return;
        }

        const files = Array.from(fileList);
        const validFiles = files.filter(file => this.validateFile(file));
        
        if (validFiles.length === 0) {
            this.showToast('请选择有效的图片文件', 'error');
            return;
        }

        await this.uploadFiles(validFiles);
    }

    validateFile(file) {
        if (!this.config.allowedTypes.includes(file.type)) {
            this.showToast(`${file.name} 不是支持的图片格式`, 'error');
            return false;
        }

        if (file.size > this.config.maxFileSize) {
            this.showToast(`${file.name} 超过20MB大小限制`, 'error');
            return false;
        }

        return true;
    }

    async uploadFiles(files) {
        this.state.uploadInProgress = true;
        this.elements.selectBtn.disabled = true;
        this.elements.progressContainer.style.display = 'block';
        
        const results = [];
        const errors = [];
        
        // 分批上传
        const chunks = this.chunkArray(files, this.config.uploadConcurrency);
        let processedCount = 0;
        
        for (const chunk of chunks) {
            const promises = chunk.map(file => this.uploadSingleFile(file));
            const chunkResults = await Promise.allSettled(promises);
            
            chunkResults.forEach((result, index) => {
                processedCount++;
                this.updateProgress((processedCount / files.length) * 100);
                
                if (result.status === 'fulfilled') {
                    results.push(result.value);
                } else {
                    errors.push({ file: chunk[index].name, error: result.reason });
                }
            });
        }
        
        this.finishUpload(results, errors);
    }

    async uploadSingleFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '上传失败');
        }
        
        return await response.json();
    }

    finishUpload(results, errors) {
        this.state.uploadInProgress = false;
        this.elements.selectBtn.disabled = false;
        this.elements.progressContainer.style.display = 'none';
        this.updateProgress(0);
        this.elements.fileInput.value = '';
        
        if (results.length > 0) {
            this.showResults(results);
            this.showToast(`成功上传 ${results.length} 个文件`, 'success');
            this.loadStats(); // 刷新统计
        }
        
        if (errors.length > 0) {
            console.error('Upload errors:', errors);
        }
    }

    showResults(results) {
        this.elements.resultsContainer.innerHTML = '';
        this.elements.resultsContainer.style.display = 'block';
        
        results.forEach(result => {
            const item = this.createResultItem(result);
            this.elements.resultsContainer.appendChild(item);
        });
        
        // 滚动到结果区域
        this.elements.resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    createResultItem(result) {
        const item = document.createElement('div');
        item.className = 'result-item';
        
        // 创建一个唯一的ID用于图片加载状态跟踪
        const imageId = `img-${result.id || Date.now()}`;
        
        item.innerHTML = `
            <div class="result-preview-container">
                <img id="${imageId}" 
                     class="result-preview" 
                     alt="预览" 
                     loading="lazy"
                     crossorigin="anonymous">
                <div class="image-loading">
                    <div class="loading-spinner"></div>
                    <span>加载中...</span>
                </div>
                <div class="image-error" style="display: none;">
                    <span>❌</span>
                    <span>加载失败</span>
                    <button class="retry-btn">重试</button>
                </div>
            </div>
            <div class="result-details">
                <div class="result-file-info">
                    <div class="result-filename">${result.filename || '未命名图片'}</div>
                    <div class="result-meta">
                        ${this.formatBytes(result.size)} • ${result.format || 'JPG'} • ${result.id?.substring(0, 8)}...
                        ${result.cdn_cached ? ' • <span style="color: var(--primary)">CDN已缓存</span>' : ''}
                    </div>
                </div>
                <div class="copy-formats">
                    ${this.createCopyFormat('URL', result.url)}
                    ${this.createCopyFormat('Markdown', `![image](${result.url})`)}
                    ${this.createCopyFormat('BBCode', `[img]${result.url}[/img]`)}
                    ${this.createCopyFormat('HTML', `<img src="${result.url}" alt="image">`)}
                </div>
            </div>
        `;
        
        // 处理图片加载
        const img = item.querySelector(`#${imageId}`);
        const loadingEl = item.querySelector('.image-loading');
        const errorEl = item.querySelector('.image-error');
        const retryBtn = item.querySelector('.retry-btn');
        
        // 图片加载处理函数
        const loadImage = (url, isRetry = false) => {
            // 显示加载状态
            loadingEl.style.display = 'flex';
            errorEl.style.display = 'none';
            img.style.display = 'none';
            
            // 设置超时
            const timeout = setTimeout(() => {
                loadingEl.style.display = 'none';
                errorEl.style.display = 'flex';
                img.style.display = 'none';
            }, this.config.imageLoadTimeout);
            
            // 创建新的图片元素来测试加载
            const testImg = new Image();
            testImg.crossOrigin = 'anonymous';
            
            testImg.onload = () => {
                clearTimeout(timeout);
                img.src = url;
                loadingEl.style.display = 'none';
                errorEl.style.display = 'none';
                img.style.display = 'block';
                
                if (isRetry) {
                    this.showToast('图片加载成功', 'success');
                }
            };
            
            testImg.onerror = () => {
                clearTimeout(timeout);
                loadingEl.style.display = 'none';
                errorEl.style.display = 'flex';
                img.style.display = 'none';
                
                // 如果是新上传的图片，可能需要等待一下再试
                if (!isRetry && result.cdn_url && !result.cdn_cached) {
                    console.log('新上传的图片可能还未缓存，5秒后自动重试...');
                    setTimeout(() => {
                        loadImage(url, true);
                    }, 5000);
                }
            };
            
            // 开始加载
            testImg.src = url;
        };
        
        // 立即加载图片
        loadImage(result.url);
        
        // 重试按钮
        retryBtn?.addEventListener('click', () => {
            loadImage(result.url, true);
        });
        
        // 绑定复制按钮事件
        item.querySelectorAll('.btn-copy').forEach((btn, index) => {
            const formats = ['URL', 'Markdown', 'BBCode', 'HTML'];
            const values = [
                result.url,
                `![image](${result.url})`,
                `[img]${result.url}[/img]`,
                `<img src="${result.url}" alt="image">`
            ];
            
            btn.addEventListener('click', () => {
                this.copyToClipboard(values[index], formats[index]);
            });
        });
        
        return item;
    }

    createCopyFormat(label, value) {
        return `
            <div class="copy-format">
                <span class="format-label">${label}:</span>
                <div class="format-value-container">
                    <span class="format-value" title="${value}">${value}</span>
                    <button class="btn-copy" type="button">复制</button>
                </div>
            </div>
        `;
    }

    // 统计功能
    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            this.state.stats = data;
            this.updateStatsDisplay();
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    updateStatsDisplay() {
        const { stats } = this.state;
        
        if (this.elements.totalFiles) {
            this.elements.totalFiles.textContent = stats.total_files || '0';
        }
        
        if (this.elements.totalSize) {
            this.elements.totalSize.textContent = this.formatBytes(stats.total_size || 0);
        }
        
        if (this.elements.uptime) {
            this.elements.uptime.textContent = this.formatUptime(stats.uptime || 0);
        }
        
        if (this.elements.uploadSpeed) {
            this.elements.uploadSpeed.textContent = stats.web_files || '0';
        }
        
        if (this.elements.cdnCached) {
            this.elements.cdnCached.textContent = stats.cdn_stats?.cached_files || '0';
        }
    }

    startStatsUpdater() {
        // 每30秒更新一次统计
        setInterval(() => this.loadStats(), 30000);
        
        // 每分钟更新运行时间
        setInterval(() => {
            if (this.state.stats.uptime) {
                this.state.stats.uptime += 60;
                this.updateStatsDisplay();
            }
        }, 60000);
    }

    // 管理员功能
    async checkAdminStatus() {
        try {
            const response = await fetch('/api/admin/check', { 
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });
            if (response.ok) {
                const data = await response.json();
                if (data.authenticated) {
                    this.showAdminUI(data.username);
                }
            }
        } catch (error) {
            console.error('Failed to check admin status:', error);
        }
    }

    showAdminUI(username) {
        this.state.adminLoggedIn = true;
        if (this.elements.adminStatus) {
            this.elements.adminStatus.style.display = 'flex';
            this.elements.adminUserDisplay.textContent = `👤 ${username}`;
        }
    }

    async handleAdminLogout() {
        try {
            await fetch('/api/admin/logout', {
                method: 'POST',
                credentials: 'include'
            });
            
            this.state.adminLoggedIn = false;
            this.elements.adminStatus.style.display = 'none';
            this.showToast('已退出管理员登录', 'info');
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    // 工具函数
    updateProgress(percent) {
        this.elements.progressFill.style.width = `${percent}%`;
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) return `${days}天${hours}时`;
        if (hours > 0) return `${hours}时${minutes}分`;
        return `${minutes}分钟`;
    }

    async copyToClipboard(text, format = '') {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast(`已复制${format}`, 'success');
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
            this.showToast(`已复制${format}`, 'success');
        }
    }

    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${message}</span>
        `;
        
        this.elements.toastContainer.appendChild(toast);
        
        // 触发回流以启动动画
        toast.offsetHeight;
        
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    chunkArray(array, size) {
        const chunks = [];
        for (let i = 0; i < array.length; i += size) {
            chunks.push(array.slice(i, i + size));
        }
        return chunks;
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.imagebed = new TelegramImageBed();
});