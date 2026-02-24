#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 路由层模块 - Flask Blueprint 组织

包含：
- upload: 上传相关路由
- images: 图片访问和查询路由
- admin: 管理员路由
- auth: Token 认证路由
- gallery_site: 画集站点公开路由
"""

from flask import Blueprint

# 创建蓝图
upload_bp = Blueprint('upload', __name__)
images_bp = Blueprint('images', __name__)
admin_bp = Blueprint('admin', __name__)
auth_bp = Blueprint('auth', __name__)
gallery_site_bp = Blueprint('gallery_site', __name__)


def register_blueprints(app):
    """注册所有蓝图到 Flask 应用"""
    # 导入路由模块以注册路由
    from . import upload, images, admin, auth, settings, galleries, tg_auth, admin_domains, gallery_site

    app.register_blueprint(upload_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    # gallery_site_bp 在 images_bp 之前注册，避免被 catch-all 路由拦截
    app.register_blueprint(gallery_site_bp)
    app.register_blueprint(images_bp)


__all__ = [
    'upload_bp', 'images_bp', 'admin_bp', 'auth_bp', 'gallery_site_bp',
    'register_blueprints',
]
