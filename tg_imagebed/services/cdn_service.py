#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDN 服务模块 - Cloudflare CDN 管理

包含：
- CloudflareCDN 类：CDN 操作封装
- CDN 缓存监控线程
- 缓存预热功能
"""
import time
import queue
import asyncio
import threading
from typing import List, Optional

import requests
import aiohttp

from ..config import (
    CLOUDFLARE_CDN_DOMAIN, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID,
    CDN_ENABLED, CDN_MONITOR_ENABLED, CDN_MONITOR_INTERVAL,
    CDN_MONITOR_MAX_RETRIES, CDN_MONITOR_QUEUE_SIZE,
    ENABLE_CACHE_WARMING, CACHE_WARMING_DELAY,
    logger
)
from ..database import update_cdn_cache_status, get_file_info, get_uncached_files


class CloudflareCDN:
    """Cloudflare CDN 管理类"""

    def __init__(self):
        self.api_token = CLOUDFLARE_API_TOKEN
        self.zone_id = CLOUDFLARE_ZONE_ID
        self.cdn_domain = CLOUDFLARE_CDN_DOMAIN
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://api.cloudflare.com/client/v4'

    def purge_cache(self, urls: List[str]) -> bool:
        """清除指定URL的缓存"""
        if not self.api_token or not self.zone_id:
            return False

        try:
            response = requests.post(
                f'{self.base_url}/zones/{self.zone_id}/purge_cache',
                headers=self.headers,
                json={'files': urls}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cloudflare缓存清除失败: {e}")
            return False

    def purge_all(self) -> bool:
        """清除所有缓存"""
        if not self.api_token or not self.zone_id:
            return False

        try:
            response = requests.post(
                f'{self.base_url}/zones/{self.zone_id}/purge_cache',
                headers=self.headers,
                json={'purge_everything': True}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cloudflare全量缓存清除失败: {e}")
            return False

    def check_cdn_status(self, encrypted_id: str) -> bool:
        """检查图片是否被CDN缓存"""
        if not self.cdn_domain:
            return False

        try:
            cdn_url = f"https://{self.cdn_domain}/image/{encrypted_id}"

            headers = {
                'User-Agent': 'CDN-Status-Checker/1.0',
                'X-CDN-Check': 'true',
                'X-Skip-Redirect': 'true'
            }

            response = requests.head(
                cdn_url,
                timeout=10,
                allow_redirects=False,
                headers=headers
            )

            # 如果返回302重定向，说明还未缓存
            if response.status_code == 302:
                logger.debug(f"图片 {encrypted_id} 返回302重定向，未被CDN缓存")
                return False

            # 检查CF-Cache-Status头部
            cache_status = response.headers.get('CF-Cache-Status', '')

            # HIT、STALE、UPDATING、REVALIDATED都认为是已缓存
            cached = cache_status in ['HIT', 'STALE', 'UPDATING', 'REVALIDATED']

            # 如果状态码是200且有缓存状态，也认为是已缓存
            if response.status_code == 200 and cache_status:
                cached = True

            if cached:
                logger.info(f"图片 {encrypted_id} CDN缓存状态: {cache_status}")
            else:
                logger.debug(f"图片 {encrypted_id} CDN缓存状态: {cache_status or 'MISS'}")

            return cached

        except requests.exceptions.Timeout:
            logger.warning(f"检查CDN状态超时 {encrypted_id}")
            return False
        except Exception as e:
            logger.debug(f"检查CDN状态失败 {encrypted_id}: {e}")
            return False

    async def warm_cache(self, url: str, encrypted_id: Optional[str] = None):
        """预热缓存"""
        if not ENABLE_CACHE_WARMING:
            return

        if not encrypted_id and '/image/' in url:
            encrypted_id = url.split('/image/')[-1].split('?')[0]

        await asyncio.sleep(CACHE_WARMING_DELAY)

        try:
            edge_locations = ['sfo', 'lax', 'ord', 'dfw', 'iad', 'lhr', 'fra', 'nrt', 'sin']

            async with aiohttp.ClientSession() as session:
                tasks = []
                for location in edge_locations:
                    headers = {
                        'CF-IPCountry': location.upper(),
                        'User-Agent': 'Cloudflare-Cache-Warmer/1.0',
                        'X-Cache-Warming': 'true'
                    }
                    task = session.get(url, headers=headers, timeout=10, allow_redirects=True)
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status in [200, 304])
                logger.info(f"缓存预热完成: {url}, 成功: {success_count}/{len(edge_locations)}")

                if success_count > 0 and encrypted_id:
                    update_cdn_cache_status(encrypted_id, True)

        except Exception as e:
            logger.error(f"缓存预热失败: {e}")


# 全局 CDN 实例
cloudflare_cdn = CloudflareCDN()

# CDN 缓存监控队列
cdn_monitor_queue: queue.Queue = queue.Queue(maxsize=CDN_MONITOR_QUEUE_SIZE)
_cdn_monitor_thread: Optional[threading.Thread] = None
_cdn_monitor_running = False


def _cdn_cache_monitor_worker():
    """CDN缓存监控工作线程"""
    global _cdn_monitor_running

    logger.info("CDN缓存监控线程启动")

    while _cdn_monitor_running:
        try:
            # 从队列获取任务（阻塞最多5秒）
            try:
                task = cdn_monitor_queue.get(timeout=5)
            except queue.Empty:
                continue

            if task is None:  # 停止信号
                break

            encrypted_id = task['encrypted_id']
            retries = task.get('retries', 0)

            # 检查是否已经缓存
            file_info = get_file_info(encrypted_id)
            if file_info and file_info.get('cdn_cached'):
                logger.debug(f"图片 {encrypted_id} 已标记为缓存，跳过检查")
                continue

            # 检查CDN缓存状态
            is_cached = cloudflare_cdn.check_cdn_status(encrypted_id)

            if is_cached:
                update_cdn_cache_status(encrypted_id, True)
                logger.info(f"✅ 图片 {encrypted_id} 已被CDN缓存（第{retries + 1}次检查）")
            else:
                if retries < CDN_MONITOR_MAX_RETRIES:
                    time.sleep(CDN_MONITOR_INTERVAL)
                    task['retries'] = retries + 1

                    try:
                        cdn_monitor_queue.put(task, block=False)
                        logger.debug(f"图片 {encrypted_id} 第{retries + 1}次检查未缓存，继续监测...")
                    except queue.Full:
                        logger.warning(f"CDN监控队列已满，放弃监控 {encrypted_id}")
                else:
                    logger.warning(f"图片 {encrypted_id} 在{CDN_MONITOR_MAX_RETRIES * CDN_MONITOR_INTERVAL}秒内未被缓存")

                    # 尝试主动预热
                    if ENABLE_CACHE_WARMING and CLOUDFLARE_CDN_DOMAIN:
                        cdn_url = f"https://{CLOUDFLARE_CDN_DOMAIN}/image/{encrypted_id}"
                        logger.info(f"尝试主动预热CDN: {encrypted_id}")

                        try:
                            response = requests.get(cdn_url, timeout=30)
                            if response.status_code == 200:
                                logger.info(f"CDN预热成功: {encrypted_id}")
                                time.sleep(5)
                                if cloudflare_cdn.check_cdn_status(encrypted_id):
                                    update_cdn_cache_status(encrypted_id, True)
                        except Exception as e:
                            logger.error(f"CDN预热失败: {e}")

        except Exception as e:
            logger.error(f"CDN监控线程错误: {e}")
            time.sleep(1)

    logger.info("CDN缓存监控线程已停止")


def start_cdn_monitor():
    """启动CDN监控线程"""
    global _cdn_monitor_thread, _cdn_monitor_running

    if not CDN_ENABLED or not CLOUDFLARE_CDN_DOMAIN or not CDN_MONITOR_ENABLED:
        logger.info("CDN监控未启用")
        return

    if _cdn_monitor_thread and _cdn_monitor_thread.is_alive():
        logger.warning("CDN监控线程已在运行")
        return

    _cdn_monitor_running = True
    _cdn_monitor_thread = threading.Thread(target=_cdn_cache_monitor_worker, daemon=True)
    _cdn_monitor_thread.start()
    logger.info("CDN监控已启动")

    # 恢复未完成的监控任务
    _restore_cdn_monitor_tasks()


def stop_cdn_monitor():
    """停止CDN监控线程"""
    global _cdn_monitor_running, _cdn_monitor_thread

    if not _cdn_monitor_thread:
        return

    logger.info("正在停止CDN监控...")
    _cdn_monitor_running = False

    try:
        cdn_monitor_queue.put(None, block=False)
    except Exception:
        pass

    if _cdn_monitor_thread.is_alive():
        _cdn_monitor_thread.join(timeout=10)

    logger.info("CDN监控已停止")


def add_to_cdn_monitor(encrypted_id: str, upload_time: Optional[int] = None):
    """添加图片到CDN监控队列"""
    # 必须同时满足：CDN启用、CDN域名配置、监控启用
    if not CDN_ENABLED or not CDN_MONITOR_ENABLED or not CLOUDFLARE_CDN_DOMAIN:
        return

    task = {
        'encrypted_id': encrypted_id,
        'upload_time': upload_time or int(time.time()),
        'retries': 0
    }

    try:
        cdn_monitor_queue.put(task, block=False)
        logger.info(f"图片 {encrypted_id} 已加入CDN监控队列")
    except queue.Full:
        logger.warning(f"CDN监控队列已满，无法添加 {encrypted_id}")


def _restore_cdn_monitor_tasks():
    """恢复未完成的CDN监控任务"""
    try:
        # 查找未缓存的近期图片（24小时内）
        since_timestamp = int(time.time()) - 86400
        rows = get_uncached_files(since_timestamp, limit=100)

        if rows:
            logger.info(f"恢复 {len(rows)} 个CDN监控任务")
            for row in rows:
                add_to_cdn_monitor(row['encrypted_id'], row['upload_time'])

    except Exception as e:
        logger.error(f"恢复CDN监控任务失败: {e}")


def get_monitor_queue_size() -> int:
    """获取监控队列大小"""
    return cdn_monitor_queue.qsize() if CDN_MONITOR_ENABLED else 0


__all__ = [
    'CloudflareCDN', 'cloudflare_cdn',
    'cdn_monitor_queue', 'start_cdn_monitor', 'stop_cdn_monitor',
    'add_to_cdn_monitor', 'get_monitor_queue_size',
]
