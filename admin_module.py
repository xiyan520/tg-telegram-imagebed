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

# 默认管理员配置
DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", "3600"))  # 默认1小时

# 配置文件路径
CONFIG_FILE = os.getenv("ADMIN_CONFIG_FILE", "admin_config.db")

def init_admin_config():
    """初始化管理员配置数据库"""
    conn = sqlite3.connect(CONFIG_FILE)
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
        password_hash = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
        cursor.execute("INSERT INTO admin_config (key, value) VALUES (?, ?)", 
                      ('password_hash', password_hash))
    
    conn.commit()
    conn.close()

def get_admin_config():
    """获取管理员配置"""
    init_admin_config()
    
    conn = sqlite3.connect(CONFIG_FILE)
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
    conn = sqlite3.connect(CONFIG_FILE)
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
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return stored_hash[0] == password_hash

def update_admin_credentials(new_username=None, new_password=None):
    """更新管理员凭据"""
    conn = sqlite3.connect(CONFIG_FILE)
    cursor = conn.cursor()
    
    try:
        if new_username:
            cursor.execute('''
                INSERT OR REPLACE INTO admin_config (key, value, updated_at) 
                VALUES ('username', ?, CURRENT_TIMESTAMP)
            ''', (new_username,))
        
        if new_password:
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
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
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def init_database_admin_update(DATABASE_PATH):
    """为管理功能更新数据库索引"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
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
    
    # 添加管理页面路由
    @app.route('/admin')
    def admin_page():
        """管理后台首页"""
        static_version = os.getenv("STATIC_VERSION", str(int(time.time())))
        force_refresh = os.getenv("FORCE_REFRESH", "false").lower() == "true"
        response = make_response(render_template('admin.html',
                                              static_version=static_version,
                                              force_refresh=force_refresh,
                                              get_static_file_version=get_static_file_version))
        return add_cache_headers(response, 'no-cache')
    
    @app.route('/admin/login')
    def admin_login():
        """管理员登录页面"""
        if session.get('admin_logged_in'):
            return redirect(url_for('admin_page'))
        static_version = os.getenv("STATIC_VERSION", str(int(time.time())))
        force_refresh = os.getenv("FORCE_REFRESH", "false").lower() == "true"
        response = make_response(render_template('admin.html',
                                              static_version=static_version,
                                              force_refresh=force_refresh,
                                              get_static_file_version=get_static_file_version))
        return add_cache_headers(response, 'no-cache')

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

    @app.route('/api/admin/login', methods=['POST'])
    def admin_login_api():
        """管理员登录"""
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
        
        # 验证用户名和密码
        if verify_admin_password(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session.permanent = True
            
            logger.info(f"管理员登录成功: {username}")
            return jsonify({'success': True, 'username': username})
        
        logger.warning(f"管理员登录失败: {username}")
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

    @app.route('/api/admin/logout', methods=['POST'])
    def admin_logout():
        """管理员退出登录"""
        username = session.get('admin_username', 'unknown')
        session.pop('admin_logged_in', None)
        session.pop('admin_username', None)
        logger.info(f"管理员退出登录: {username}")
        return jsonify({'success': True})
    
    @app.route('/api/admin/update_credentials', methods=['POST'])
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

    @app.route('/api/admin/stats')
    @login_required
    def admin_stats():
        """获取管理统计信息"""
        total_files = get_all_files_count()
        total_size = get_total_size()
        
        # 获取今日上传数
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        try:
            today = datetime.now().date()
            cursor.execute('''
                SELECT COUNT(*) FROM file_storage 
                WHERE DATE(created_at) = DATE(?)
            ''', (today,))
            today_uploads = cursor.fetchone()[0]
        except:
            today_uploads = 0
        finally:
            conn.close()
        
        return jsonify({
            'total_files': total_files,
            'total_size': total_size,
            'today_uploads': today_uploads
        })

    @app.route('/api/admin/images')
    @login_required
    def admin_images():
        """获取图片列表（支持分页和搜索）"""
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '').strip()
        
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 构建查询
            offset = (page - 1) * limit
            
            # 简化查询，只包含基本字段
            query = '''
                SELECT 
                    fs.encrypted_id, 
                    fs.file_id, 
                    fs.original_filename, 
                    fs.file_size, 
                    fs.source, 
                    fs.created_at, 
                    fs.username, 
                    fs.access_count, 
                    fs.last_accessed,
                    fs.upload_time,
                    fs.cdn_cached,
                    fs.cdn_cache_time,
                    fs.mime_type
                FROM file_storage fs
            '''
            params = []
            
            if search:
                # 搜索文件名和用户名
                query += ' WHERE fs.original_filename LIKE ? OR fs.username LIKE ?'
                search_pattern = f'%{search}%'
                params.extend([search_pattern, search_pattern])
            
            # 获取总数
            count_query = 'SELECT COUNT(*) FROM file_storage'
            if search:
                count_query += ' WHERE original_filename LIKE ? OR username LIKE ?'
                cursor.execute(count_query, params)
            else:
                cursor.execute(count_query)
            
            total_count = cursor.fetchone()[0]
            
            # 获取当前页数据
            query += ' ORDER BY fs.created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            images = []
            
            for row in cursor.fetchall():
                image_data = dict(row)
                
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
            
            return jsonify({
                'success': True,
                'images': images,
                'total': total_count,
                'page': page,
                'limit': limit,
                'total_pages': total_pages,
                'total_count': total_count
            })
            
        except Exception as e:
            logger.error(f"获取图片列表失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': '获取图片列表失败'}), 500
        finally:
            conn.close()

    @app.route('/api/admin/images/delete', methods=['POST'])
    @login_required
    def admin_delete_images():
        """删除图片"""
        data = request.get_json()
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({'success': False, 'error': '没有选择要删除的图片'}), 400
        
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
                'deleted': deleted_count,
                'message': f'成功删除 {deleted_count} 张图片'
            })
            
        except Exception as e:
            logger.error(f"删除图片失败: {e}")
            conn.rollback()
            return jsonify({'success': False, 'error': '删除失败'}), 500
        finally:
            conn.close()
    
    logger.info("管理员路由注册完成")