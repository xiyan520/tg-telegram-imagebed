#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram图床机器人 - 管理员功能模块（简化版）
提供Web管理后台功能
"""
import os
import sqlite3
import hashlib
import secrets
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify, render_template, make_response, redirect, url_for

# 日志配置
logger = logging.getLogger(__name__)

# 从 utils.py 导入 get_domain
try:
    from .utils import get_domain
except ImportError:
    # 兼容独立运行场景
    def get_domain(req):
        """简化版 get_domain 函数"""
        return req.host_url.rstrip('/')

# 从 config.py 导入配置（统一配置来源，避免默认弱口令）
try:
    from .config import (
        DEFAULT_ADMIN_USERNAME,
        DEFAULT_ADMIN_PASSWORD,
        SESSION_LIFETIME,
        DATABASE_PATH
    )
except ImportError:
    # 兼容独立运行场景
    DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    # 无默认密码，必须从环境变量读取
    DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    if not DEFAULT_ADMIN_PASSWORD:
        import secrets
        DEFAULT_ADMIN_PASSWORD = secrets.token_urlsafe(12)
        logger.warning("ADMIN_PASSWORD 未配置，已自动生成临时密码")
    SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", "3600"))
    DEFAULT_DB_PATH = os.path.join(os.getcwd(), "telegram_imagebed.db")
    DATABASE_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)


def _get_config_status_from_db() -> dict:
    """从数据库读取配置状态（回退到环境变量）"""
    cdn_enabled = os.getenv('CDN_ENABLED', 'false').lower() == 'true'
    group_upload_enabled = os.getenv('ENABLE_GROUP_UPLOAD', 'false').lower() == 'true'
    cdn_monitor_enabled = os.getenv('CDN_MONITOR_ENABLED', 'false').lower() == 'true'
    cdn_domain = (os.getenv('CLOUDFLARE_CDN_DOMAIN') or '').strip()

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM admin_config WHERE key = ?", ('cdn_enabled',))
        row = cursor.fetchone()
        if row is not None:
            cdn_enabled = str(row[0]) == '1'

        cursor.execute("SELECT value FROM admin_config WHERE key = ?", ('group_upload_enabled',))
        row = cursor.fetchone()
        if row is not None:
            group_upload_enabled = str(row[0]) == '1'

        cursor.execute("SELECT value FROM admin_config WHERE key = ?", ('cdn_monitor_enabled',))
        row = cursor.fetchone()
        if row is not None:
            cdn_monitor_enabled = str(row[0]) == '1'

        cursor.execute("SELECT value FROM admin_config WHERE key = ?", ('cloudflare_cdn_domain',))
        row = cursor.fetchone()
        if row is not None:
            cdn_domain = str(row[0] or '').strip()

        conn.close()
    except Exception as e:
        logger.debug(f"从数据库读取系统设置失败（回退到环境变量）: {e}")

    return {
        'cdnStatus': '已启用' if cdn_enabled else '未启用',
        'cdnDomain': cdn_domain if cdn_domain else '未配置',
        'uptime': '运行中',
        'groupUpload': '已启用' if group_upload_enabled else '未启用',
        'cdnMonitor': '已启用' if cdn_monitor_enabled else '未启用'
    }

def init_admin_config():
    """初始化管理员配置表（在主数据库中）"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 检查是否有配置，如果没有则使用默认值
    cursor.execute("SELECT value FROM admin_config WHERE key = 'username'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO admin_config (key, value) VALUES (?, ?)", 
                      ('username', DEFAULT_ADMIN_USERNAME))
    
    cursor.execute("SELECT value FROM admin_config WHERE key = 'password_hash'")
    if not cursor.fetchone():
        # 使用 werkzeug.security 进行安全的密码哈希
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(DEFAULT_ADMIN_PASSWORD, method='pbkdf2:sha256')
        cursor.execute("INSERT INTO admin_config (key, value) VALUES (?, ?)",
                      ('password_hash', password_hash))
    
    conn.commit()
    conn.close()

def get_admin_config():
    """获取管理员配置"""
    init_admin_config()

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM admin_config WHERE key = 'username'")
    username = cursor.fetchone()
    username = username[0] if username else DEFAULT_ADMIN_USERNAME
    
    cursor.execute("SELECT value FROM admin_config WHERE key = 'password_hash'")
    password_hash = cursor.fetchone()
    
    conn.close()
    
    return {
        'username': username,
        'password_status': '已设置' if password_hash else '使用默认密码',
        'session_lifetime': SESSION_LIFETIME
    }

def verify_admin_password(username, password):
    """验证管理员密码"""
    from werkzeug.security import check_password_hash

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM admin_config WHERE key = 'username'")
    stored_username = cursor.fetchone()
    if not stored_username or stored_username[0] != username:
        conn.close()
        return False

    cursor.execute("SELECT value FROM admin_config WHERE key = 'password_hash'")
    stored_hash = cursor.fetchone()

    conn.close()

    if not stored_hash:
        return False

    # 使用 werkzeug.security 验证密码
    # 兼容旧的 sha256 哈希格式
    hash_value = stored_hash[0]
    if hash_value.startswith('pbkdf2:'):
        return check_password_hash(hash_value, password)
    else:
        # 兼容旧格式（sha256）
        import hashlib
        return hash_value == hashlib.sha256(password.encode()).hexdigest()

def update_admin_credentials(new_username=None, new_password=None):
    """更新管理员凭据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        if new_username:
            cursor.execute('''
                INSERT OR REPLACE INTO admin_config (key, value, updated_at) 
                VALUES ('username', ?, CURRENT_TIMESTAMP)
            ''', (new_username,))
        
        if new_password:
            # 使用 werkzeug.security 进行安全的密码哈希
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
            cursor.execute('''
                INSERT OR REPLACE INTO admin_config (key, value, updated_at)
                VALUES ('password_hash', ?, CURRENT_TIMESTAMP)
            ''', (password_hash,))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"更新管理员凭据失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def configure_admin_session(app):
    """配置管理员会话"""
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_SECURE', 'false').lower() == 'true'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_LIFETIME)

# 添加登录验证装饰器
def login_required(f):
    """需要登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 处理OPTIONS预检请求
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            if request.path.startswith('/api/'):
                response = jsonify({'error': 'Unauthorized'})
                response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                return response, 401
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def init_database_admin_update(DATABASE_PATH):
    """为管理功能更新数据库索引"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # 检查并添加新列
        cursor.execute("PRAGMA table_info(file_storage)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 添加缺失的列
        if 'is_group_upload' not in columns:
            logger.info("管理模块：添加 is_group_upload 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN is_group_upload BOOLEAN DEFAULT 0')
        
        if 'group_message_id' not in columns:
            logger.info("管理模块：添加 group_message_id 列")
            cursor.execute('ALTER TABLE file_storage ADD COLUMN group_message_id INTEGER')
        
        # 添加文件名索引以加速搜索
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_original_filename 
            ON file_storage(original_filename)
        ''')
        
        # 添加额外的索引以优化管理查询
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON file_storage(created_at DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_size ON file_storage(file_size)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_group_upload ON file_storage(is_group_upload)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("管理功能数据库索引创建完成")
    except Exception as e:
        logger.error(f"创建管理索引失败: {e}")

def get_static_file_version(filename):
    """获取静态文件版本号"""
    # 如果启用了强制刷新，总是返回当前时间戳
    force_refresh = os.getenv("FORCE_REFRESH", "false").lower() == "true"
    if force_refresh:
        return str(int(time.time()))
    
    # 否则返回配置的静态版本
    return os.getenv("STATIC_VERSION", str(int(time.time())))

def register_admin_routes(app, DATABASE_PATH, get_all_files_count, get_total_size, add_cache_headers):
    """注册管理员路由"""

    # 注意：/admin 和 /admin/login 页面路由已移除
    # 这些路由由前端 SPA (frontend/.output/public/admin/) 处理
    # Flask 通过 serve_frontend() 提供静态文件

    # 添加管理相关API路由
    @app.route('/api/admin/check')
    def admin_check():
        """检查管理员登录状态"""
        if 'admin_logged_in' in session and session['admin_logged_in']:
            return jsonify({
                'authenticated': True,
                'username': session.get('admin_username', 'admin')
            })
        return jsonify({'authenticated': False})

    @app.route('/api/admin/login', methods=['POST', 'OPTIONS'])
    def admin_login_api():
        """管理员登录"""
        # 处理OPTIONS预检请求
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            response = jsonify({'success': False, 'message': '用户名和密码不能为空'})
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response, 400

        # 验证用户名和密码
        if verify_admin_password(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session.permanent = True

            # 生成一个简单的 token（用于前端存储）
            token = secrets.token_urlsafe(32)
            session['admin_token'] = token

            logger.info(f"管理员登录成功: {username}")
            response = jsonify({
                'success': True,
                'data': {
                    'token': token,
                    'username': username
                }
            })
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        logger.warning(f"管理员登录失败: {username}")
        response = jsonify({'success': False, 'message': '用户名或密码错误'})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response, 401

    @app.route('/api/admin/logout', methods=['POST', 'OPTIONS'])
    def admin_logout():
        """管理员退出登录"""
        # 处理OPTIONS预检请求
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response

        username = session.get('admin_username', 'unknown')
        session.pop('admin_logged_in', None)
        session.pop('admin_username', None)
        logger.info(f"管理员退出登录: {username}")
        response = jsonify({'success': True})
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    @app.route('/api/admin/update_credentials', methods=['POST', 'OPTIONS'])
    @login_required
    def admin_update_credentials():
        """更新管理员凭据"""
        data = request.get_json()
        new_username = data.get('username', '').strip()
        new_password = data.get('password', '').strip()
        
        if not new_username and not new_password:
            return jsonify({'success': False, 'error': '请提供新的用户名或密码'}), 400
        
        if new_username and len(new_username) < 3:
            return jsonify({'success': False, 'error': '用户名至少需要3个字符'}), 400
        
        if new_password and len(new_password) < 6:
            return jsonify({'success': False, 'error': '密码至少需要6个字符'}), 400
        
        if update_admin_credentials(new_username, new_password):
            # 如果更改了用户名，更新会话
            if new_username:
                session['admin_username'] = new_username
            
            return jsonify({
                'success': True, 
                'message': '凭据更新成功',
                'updated_username': new_username is not None,
                'updated_password': new_password is not None
            })
        
        return jsonify({'success': False, 'error': '更新失败'}), 500

    @app.route('/api/admin/stats', methods=['GET', 'OPTIONS'])
    @login_required
    def admin_stats():
        """获取管理统计信息"""
        try:
            total_files = get_all_files_count()
            total_size = get_total_size()

            # 获取今日上传数
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            try:
                # 修复日期查询 - 使用时间戳范围查询
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                today_start_ts = int(today_start.timestamp())
                today_end_ts = int(today_end.timestamp())

                cursor.execute('''
                    SELECT COUNT(*) FROM file_storage
                    WHERE upload_time >= ? AND upload_time <= ?
                ''', (today_start_ts, today_end_ts))
                today_uploads = cursor.fetchone()[0]

                # 获取 CDN 缓存数量
                cursor.execute('SELECT COUNT(*) FROM file_storage WHERE cdn_cached = 1')
                cdn_cached = cursor.fetchone()[0]
            except Exception as e:
                logger.error(f"查询统计数据失败: {e}")
                today_uploads = 0
                cdn_cached = 0
            finally:
                conn.close()

            # 格式化文件大小
            def format_size(size_bytes):
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    return f"{size_bytes / 1024 / 1024:.1f} MB"
                else:
                    return f"{size_bytes / 1024 / 1024 / 1024:.1f} GB"

            response_data = {
                'success': True,
                'data': {
                    'stats': {
                        'totalImages': total_files,
                        'totalSize': format_size(total_size),
                        'todayUploads': today_uploads,
                        'cdnCached': cdn_cached
                    },
                    'config': _get_config_status_from_db()
                }
            }

            logger.info(f"返回统计数据: {response_data}")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': '获取统计信息失败',
                'message': str(e)
            }), 500

    @app.route('/api/admin/images', methods=['GET', 'OPTIONS'])
    @login_required
    def admin_images():
        """获取图片列表（支持分页、搜索和筛选）"""
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
            search = request.args.get('search', '').strip()
            filter_type = request.args.get('filter', 'all').strip().lower()

            # 边界保护：确保 page >= 1，1 <= limit <= 200
            page = max(1, page)
            limit = max(1, min(200, limit))

            # 验证 filter 参数
            if filter_type not in ('all', 'cached', 'uncached', 'group'):
                filter_type = 'all'

            logger.info(f"获取图片列表请求: page={page}, limit={limit}, search={search}, filter={filter_type}")

            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

        except Exception as e:
            logger.error(f"初始化数据库连接失败: {e}")
            return jsonify({
                'success': False,
                'error': '数据库连接失败',
                'message': str(e)
            }), 500

        try:
            # 检查列是否存在
            cursor.execute("PRAGMA table_info(file_storage)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 构建查询
            offset = (page - 1) * limit
            
            # 构建SELECT语句，只选择存在的列
            select_columns = [
                'fs.encrypted_id', 'fs.file_id', 'fs.original_filename', 
                'fs.file_size', 'fs.source', 'fs.created_at', 'fs.username', 
                'fs.access_count', 'fs.last_accessed', 'fs.upload_time',
                'fs.cdn_cached', 'fs.cdn_cache_time', 'fs.mime_type'
            ]
            
            # 可选列
            if 'is_group_upload' in columns:
                select_columns.append('fs.is_group_upload')
            if 'cdn_hit_count' in columns:
                select_columns.append('fs.cdn_hit_count')
            if 'direct_hit_count' in columns:
                select_columns.append('fs.direct_hit_count')

            query = f'''
                SELECT {', '.join(select_columns)}
                FROM file_storage fs
            '''

            # 构建 WHERE 条件
            where_clauses = []
            where_params = []

            if search:
                # 搜索文件名和用户名
                where_clauses.append('(fs.original_filename LIKE ? OR fs.username LIKE ?)')
                search_pattern = f'%{search}%'
                where_params.extend([search_pattern, search_pattern])

            # 根据 filter_type 添加筛选条件
            if filter_type == 'cached':
                if 'cdn_cached' in columns:
                    where_clauses.append('fs.cdn_cached = 1')
                else:
                    # 如果列不存在，返回空结果
                    where_clauses.append('1 = 0')
            elif filter_type == 'uncached':
                if 'cdn_cached' in columns:
                    where_clauses.append('(fs.cdn_cached = 0 OR fs.cdn_cached IS NULL)')
                # 如果列不存在，不添加条件（相当于返回全部）
            elif filter_type == 'group':
                if 'is_group_upload' in columns:
                    where_clauses.append('fs.is_group_upload = 1')
                else:
                    # 如果列不存在，返回空结果
                    where_clauses.append('1 = 0')

            # 拼接 WHERE 子句
            if where_clauses:
                query += ' WHERE ' + ' AND '.join(where_clauses)

            # 获取总数（与查询条件一致）
            count_query = 'SELECT COUNT(*) FROM file_storage fs'
            if where_clauses:
                count_query += ' WHERE ' + ' AND '.join(where_clauses)
            cursor.execute(count_query, where_params)

            total_count = cursor.fetchone()[0]

            # 获取当前页数据
            query += ' ORDER BY fs.created_at DESC LIMIT ? OFFSET ?'
            params = list(where_params)
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            images = []
            
            for row in cursor.fetchall():
                image_data = dict(row)
                
                # 如果没有 is_group_upload 列，默认为 0
                if 'is_group_upload' not in image_data:
                    image_data['is_group_upload'] = 0
                # 如果没有访问统计列，默认为 0
                if 'cdn_hit_count' not in image_data:
                    image_data['cdn_hit_count'] = 0
                if 'direct_hit_count' not in image_data:
                    image_data['direct_hit_count'] = 0

                # 处理时间格式
                if image_data.get('upload_time'):
                    try:
                        timestamp = int(image_data['upload_time'])
                        dt = datetime.fromtimestamp(timestamp)
                        image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.debug(f"处理upload_time失败: {e}")
                
                if 'created_at' in image_data and image_data['created_at'] and not isinstance(image_data['created_at'], str):
                    created_at = image_data['created_at']
                    try:
                        if isinstance(created_at, (int, float)):
                            dt = datetime.fromtimestamp(created_at)
                            image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            created_at_str = str(created_at)
                            if 'T' in created_at_str:
                                dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            elif ' ' in created_at_str:
                                image_data['created_at'] = created_at_str
                            else:
                                dt = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                                image_data['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.debug(f"时间格式转换失败 ({created_at}): {e}")
                        image_data['created_at'] = str(created_at) if created_at else '未知时间'
                
                # 处理最后访问时间
                if image_data.get('last_accessed'):
                    try:
                        last_accessed = image_data['last_accessed']
                        if isinstance(last_accessed, str) and 'T' in last_accessed:
                            dt = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
                            image_data['last_accessed'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(last_accessed, (int, float)):
                            dt = datetime.fromtimestamp(last_accessed)
                            image_data['last_accessed'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            image_data['last_accessed'] = str(last_accessed)
                    except Exception as e:
                        logger.debug(f"处理last_accessed失败: {e}")
                        image_data['last_accessed'] = None
                
                # 处理CDN缓存时间
                if image_data.get('cdn_cache_time'):
                    try:
                        cdn_cache_time = image_data['cdn_cache_time']
                        if isinstance(cdn_cache_time, str) and 'T' in cdn_cache_time:
                            dt = datetime.fromisoformat(cdn_cache_time.replace('Z', '+00:00'))
                            image_data['cdn_cache_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(cdn_cache_time, (int, float)):
                            dt = datetime.fromtimestamp(cdn_cache_time)
                            image_data['cdn_cache_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            image_data['cdn_cache_time'] = str(cdn_cache_time)
                    except Exception as e:
                        logger.debug(f"处理cdn_cache_time失败: {e}")
                        image_data['cdn_cache_time'] = None
                
                # 确保created_at是字符串格式
                if 'created_at' not in image_data or not image_data['created_at']:
                    image_data['created_at'] = '未知时间'
                elif not isinstance(image_data['created_at'], str):
                    image_data['created_at'] = str(image_data['created_at'])
                
                images.append(image_data)
            
            # 计算总页数
            total_pages = (total_count + limit - 1) // limit

            # 构建图片 URL（使用 get_domain 处理反向代理/CDN 场景）
            base_url = get_domain(request).rstrip('/')
            cdn_domain = os.getenv('CLOUDFLARE_CDN_DOMAIN', '')

            for img in images:
                img['url'] = f"{base_url}/image/{img['encrypted_id']}"
                if cdn_domain:
                    img['cdn_url'] = f"https://{cdn_domain}/image/{img['encrypted_id']}"
                img['id'] = img['encrypted_id']
                img['filename'] = img.get('original_filename', '未知文件')
                img['size'] = img.get('file_size', 0)
                img['uploadTime'] = img.get('created_at', '未知时间')
                img['cached'] = bool(img.get('cdn_cached', 0))

            response_data = {
                'success': True,
                'data': {
                    'images': images,
                    'totalPages': total_pages,
                    'total': total_count,
                    'page': page,
                    'limit': limit
                }
            }

            logger.info(f"成功返回图片列表: {len(images)} 张图片, 总页数: {total_pages}")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"获取图片列表失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': '获取图片列表失败',
                'message': str(e)
            }), 500
        finally:
            try:
                conn.close()
            except:
                pass

    @app.route('/api/admin/delete', methods=['POST', 'OPTIONS'])
    @login_required
    def admin_delete_images():
        """删除图片"""
        data = request.get_json()
        ids = data.get('ids', [])

        if not ids:
            return jsonify({'success': False, 'message': '没有选择要删除的图片'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        deleted_count = 0
        deleted_size = 0
        
        try:
            # 构建占位符
            placeholders = ','.join('?' * len(ids))
            
            # 先获取要删除的文件信息（用于统计）
            cursor.execute(f'''
                SELECT SUM(file_size) FROM file_storage 
                WHERE encrypted_id IN ({placeholders})
            ''', ids)
            result = cursor.fetchone()
            if result and result[0]:
                deleted_size = result[0]
            
            # 删除记录
            cursor.execute(f'''
                DELETE FROM file_storage 
                WHERE encrypted_id IN ({placeholders})
            ''', ids)
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            logger.info(f"管理员删除了 {deleted_count} 张图片")
            
            return jsonify({
                'success': True,
                'data': {
                    'deleted': deleted_count,
                    'message': f'成功删除 {deleted_count} 张图片'
                }
            })

        except Exception as e:
            logger.error(f"删除图片失败: {e}")
            conn.rollback()
            return jsonify({'success': False, 'message': '删除失败'}), 500
        finally:
            conn.close()
    
    logger.info("管理员路由注册完成")