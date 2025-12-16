#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDN 服务模块 - Cloudflare CDN 管理

包含：
- CloudflareCDN 类：CDN 操作封装
- CDN 缓存监控线程（非阻塞调度）
- 缓存预热功能
- 缓存状态探测
"""
import time
import queue
import itertools
import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import (
    CLOUDFLARE_CDN_DOMAIN, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID,
    CDN_MONITOR_INTERVAL, CDN_MONITOR_MAX_RETRIES, CDN_MONITOR_QUEUE_SIZE,
    ENABLE_CACHE_WARMING,
    logger
)
from ..database import update_cdn_cache_status, get_file_info, get_uncached_files, get_system_setting


# CDN 配置缓存（减少数据库查询）
_CDN_SETTINGS_CACHE = {
    "ts": 0.0,
    "cdn_enabled": False,
    "monitor_enabled": False,
    "cdn_domain": "",
    "api_token": "",
    "zone_id": "",
    "cache_warming_enabled": False,
}


def _get_effective_cdn_settings():
    """从数据库读取 CDN 设置（带缓存，1秒 TTL）"""
    now = time.time()
    if (now - _CDN_SETTINGS_CACHE["ts"]) < 1.0:
        return (
            _CDN_SETTINGS_CACHE["cdn_enabled"],
            _CDN_SETTINGS_CACHE["monitor_enabled"],
            _CDN_SETTINGS_CACHE["cdn_domain"],
            _CDN_SETTINGS_CACHE["api_token"],
            _CDN_SETTINGS_CACHE["zone_id"],
            _CDN_SETTINGS_CACHE["cache_warming_enabled"],
        )

    cdn_enabled = False
    monitor_enabled = False
    cdn_domain = ""
    api_token = ""
    zone_id = ""
    cache_warming_enabled = False
    try:
        cdn_enabled = str(get_system_setting("cdn_enabled") or "0") == "1"
        monitor_enabled = str(get_system_setting("cdn_monitor_enabled") or "0") == "1"
        cdn_domain = str(get_system_setting("cloudflare_cdn_domain") or "").strip()
        api_token = str(get_system_setting("cloudflare_api_token") or "").strip()
        zone_id = str(get_system_setting("cloudflare_zone_id") or "").strip()
        cache_warming_enabled = str(get_system_setting("enable_cache_warming") or "0") == "1"
    except Exception as e:
        # 数据库不可用时回退到 config 常量
        logger.debug(f"从数据库读取 CDN 设置失败，使用 config 常量: {e}")
        cdn_enabled = bool(CDN_ENABLED)
        monitor_enabled = bool(CDN_MONITOR_ENABLED)
        cdn_domain = str(CLOUDFLARE_CDN_DOMAIN or "").strip()
        api_token = str(CLOUDFLARE_API_TOKEN or "").strip()
        zone_id = str(CLOUDFLARE_ZONE_ID or "").strip()
        cache_warming_enabled = bool(ENABLE_CACHE_WARMING)

    _CDN_SETTINGS_CACHE.update({
        "ts": now,
        "cdn_enabled": cdn_enabled,
        "monitor_enabled": monitor_enabled,
        "cdn_domain": cdn_domain,
        "api_token": api_token,
        "zone_id": zone_id,
        "cache_warming_enabled": cache_warming_enabled,
    })
    return cdn_enabled, monitor_enabled, cdn_domain, api_token, zone_id, cache_warming_enabled


# CDN 缓存状态常量
CF_CACHED_STATUSES = {'HIT', 'STALE', 'UPDATING', 'REVALIDATED'}
CF_NOT_CACHED_STATUSES = {'MISS', 'BYPASS', 'DYNAMIC', 'EXPIRED'}
CF_PURGE_FILES_LIMIT = 30  # Cloudflare API 单次清除URL数量限制


@dataclass(frozen=True)
class CDNProbeResult:
    """CDN 探测结果"""
    url: str
    status_code: int
    cf_cache_status: str
    cached: bool
    age: Optional[int] = None
    cf_ray: Optional[str] = None
    error: Optional[str] = None


class CloudflareCDN:
    """Cloudflare CDN 管理类"""

    def __init__(self):
        self.api_token = ""
        self.zone_id = ""
        self.cdn_domain = ""
        self.headers = {'Content-Type': 'application/json'}
        self.base_url = 'https://api.cloudflare.com/client/v4'
        self._cfg_ts = 0.0

        # 创建带重试的 Session
        self._session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=('GET', 'HEAD', 'POST'),
            raise_on_status=False,
        )
        self._session.mount('https://', HTTPAdapter(max_retries=retry))

    def _refresh_config(self, *, force: bool = False) -> None:
        """从数据库刷新 CDN 配置"""
        now = time.time()
        if not force and (now - self._cfg_ts) < 1.0:
            return
        _cdn_enabled, _monitor_enabled, cdn_domain, api_token, zone_id, _cache_warming = _get_effective_cdn_settings()
        self.api_token = api_token
        self.zone_id = zone_id
        self.cdn_domain = cdn_domain
        headers = {'Content-Type': 'application/json'}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        self.headers = headers
        self._cfg_ts = now

    def _api_post(self, path: str, payload: dict) -> Tuple[bool, str]:
        """发送 Cloudflare API POST 请求"""
        self._refresh_config()
        if not self.api_token or not self.zone_id:
            return False, 'missing Cloudflare credentials'

        try:
            resp = self._session.post(
                f'{self.base_url}{path}',
                headers=self.headers,
                json=payload,
                timeout=20,
            )
        except Exception as e:
            return False, str(e)

        try:
            data = resp.json()
        except Exception:
            data = None

        if resp.status_code != 200:
            return False, f'http {resp.status_code}'

        if isinstance(data, dict) and data.get('success') is False:
            errs = data.get('errors') or []
            if errs and isinstance(errs[0], dict) and errs[0].get('message'):
                return False, errs[0]['message']
            return False, 'cloudflare api error'

        return True, ''

    def probe_url(self, url: str) -> CDNProbeResult:
        """
        探测 URL 的 CDN 缓存状态
        使用 Range: bytes=0-0 的轻量请求，同时可触发缓存
        """
        headers = {
            'User-Agent': 'CDN-Probe/1.0',
            'Range': 'bytes=0-0',
        }
        try:
            resp = self._session.get(url, headers=headers, timeout=15, allow_redirects=False)
            cf_cache_status = resp.headers.get('CF-Cache-Status', '')
            age_raw = resp.headers.get('Age')
            age = int(age_raw) if age_raw and str(age_raw).isdigit() else None
            cf_ray = resp.headers.get('CF-Ray')
            cached = cf_cache_status in CF_CACHED_STATUSES
            return CDNProbeResult(
                url=url,
                status_code=resp.status_code,
                cf_cache_status=cf_cache_status,
                cached=cached,
                age=age,
                cf_ray=cf_ray,
            )
        except requests.exceptions.Timeout:
            return CDNProbeResult(url=url, status_code=0, cf_cache_status='', cached=False, error='timeout')
        except Exception as e:
            return CDNProbeResult(url=url, status_code=0, cf_cache_status='', cached=False, error=str(e))

    def probe_encrypted_id(self, encrypted_id: str) -> CDNProbeResult:
        """探测指定图片的 CDN 缓存状态"""
        self._refresh_config()
        if not self.cdn_domain:
            return CDNProbeResult(
                url='', status_code=0, cf_cache_status='',
                cached=False, error='CDN domain not configured'
            )
        url = f'https://{self.cdn_domain}/image/{encrypted_id}'
        return self.probe_url(url)

    def warm_cache_sync(self, encrypted_id: str) -> bool:
        """
        同步预热缓存
        通过发送一个探测请求来触发 Cloudflare 缓存
        """
        _cdn_enabled, _monitor_enabled, _domain, _api_token, _zone_id, cache_warming_enabled = _get_effective_cdn_settings()
        self._refresh_config()
        if not cache_warming_enabled or not self.cdn_domain:
            return False

        probe = self.probe_encrypted_id(encrypted_id)
        if probe.error:
            logger.debug(f'CDN warm failed: {encrypted_id}: {probe.error}')
            return False
        return probe.status_code in (200, 206, 304)

    def purge_cache(self, urls: List[str]) -> bool:
        """清除指定URL的缓存（支持分块）"""
        self._refresh_config()
        if not self.api_token or not self.zone_id:
            return False

        if not urls:
            return True

        try:
            ok_all = True
            for i in range(0, len(urls), CF_PURGE_FILES_LIMIT):
                chunk = urls[i:i + CF_PURGE_FILES_LIMIT]
                ok, err = self._api_post(
                    f'/zones/{self.zone_id}/purge_cache',
                    {'files': chunk},
                )
                if not ok:
                    ok_all = False
                    logger.error(f'Cloudflare purge_cache failed: {err}')
            return ok_all
        except Exception as e:
            logger.error(f'Cloudflare缓存清除失败: {e}')
            return False

    def purge_by_tags(self, tags: List[str]) -> bool:
        """按 Cache-Tag 清除缓存（需要 Cloudflare Enterprise 或支持的计划）"""
        self._refresh_config()
        if not tags:
            return True

        ok, err = self._api_post(
            f'/zones/{self.zone_id}/purge_cache',
            {'tags': tags},
        )
        if not ok:
            logger.error(f'Cloudflare purge_by_tags failed: {err}')
        return ok

    def purge_all(self) -> bool:
        """清除所有缓存"""
        self._refresh_config()
        if not self.api_token or not self.zone_id:
            return False

        try:
            ok, err = self._api_post(
                f'/zones/{self.zone_id}/purge_cache',
                {'purge_everything': True},
            )
            if not ok:
                logger.error(f'Cloudflare purge_all failed: {err}')
            return ok
        except Exception as e:
            logger.error(f'Cloudflare全量缓存清除失败: {e}')
            return False

    def check_cdn_status(self, encrypted_id: str) -> bool:
        """检查图片是否被CDN缓存"""
        self._refresh_config()
        if not self.cdn_domain:
            return False

        try:
            probe = self.probe_encrypted_id(encrypted_id)
            cache_status = probe.cf_cache_status
            cached = probe.cached

            if cached:
                logger.info(f'图片 {encrypted_id} CDN缓存状态: {cache_status}')
            else:
                logger.debug(f'图片 {encrypted_id} CDN缓存状态: {cache_status or "MISS"}')

            return cached

        except requests.exceptions.Timeout:
            logger.warning(f'检查CDN状态超时 {encrypted_id}')
            return False
        except Exception as e:
            logger.debug(f'检查CDN状态失败 {encrypted_id}: {e}')
            return False


# 全局 CDN 实例
cloudflare_cdn = CloudflareCDN()

# CDN 缓存监控队列（使用 PriorityQueue 实现非阻塞延迟调度）
cdn_monitor_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=CDN_MONITOR_QUEUE_SIZE)
_cdn_monitor_seq = itertools.count()  # 用于保证相同优先级时的 FIFO 顺序
_cdn_monitor_thread: Optional[threading.Thread] = None
_cdn_monitor_running = False
_cdn_monitor_stop_event = threading.Event()


def _cdn_cache_monitor_worker():
    """CDN缓存监控工作线程（非阻塞调度）"""
    global _cdn_monitor_running

    logger.info('CDN缓存监控线程启动')

    while _cdn_monitor_running:
        try:
            # 从队列获取任务（阻塞最多1秒）
            try:
                run_at, _seq, task = cdn_monitor_queue.get(timeout=1)
            except queue.Empty:
                continue

            if task is None:  # 停止信号
                break

            now = time.time()
            if run_at > now:
                # 未到执行时间：放回队列并等待
                try:
                    cdn_monitor_queue.put((run_at, next(_cdn_monitor_seq), task), block=False)
                except queue.Full:
                    logger.warning('CDN监控队列已满，丢弃延迟任务')
                _cdn_monitor_stop_event.wait(timeout=min(run_at - now, 1.0))
                continue

            encrypted_id = task['encrypted_id']
            retries = task.get('retries', 0)

            # 首次检查时尝试主动预热（DB 控制）
            if retries == 0:
                cloudflare_cdn.warm_cache_sync(encrypted_id)

            # 检查是否已经缓存
            file_info = get_file_info(encrypted_id)
            if file_info and file_info.get('cdn_cached'):
                logger.debug(f'图片 {encrypted_id} 已标记为缓存，跳过检查')
                continue

            # 检查CDN缓存状态
            is_cached = cloudflare_cdn.check_cdn_status(encrypted_id)

            if is_cached:
                update_cdn_cache_status(encrypted_id, True)
                logger.info(f'✅ 图片 {encrypted_id} 已被CDN缓存（第{retries + 1}次检查）')
            else:
                if retries < CDN_MONITOR_MAX_RETRIES:
                    task['retries'] = retries + 1
                    try:
                        next_run = time.time() + CDN_MONITOR_INTERVAL
                        cdn_monitor_queue.put((next_run, next(_cdn_monitor_seq), task), block=False)
                        logger.debug(f'图片 {encrypted_id} 第{retries + 1}次检查未缓存，继续监测...')
                    except queue.Full:
                        logger.warning(f'CDN监控队列已满，放弃监控 {encrypted_id}')
                else:
                    logger.warning(f'图片 {encrypted_id} 在{CDN_MONITOR_MAX_RETRIES * CDN_MONITOR_INTERVAL}秒内未被缓存')

        except Exception as e:
            logger.error(f'CDN监控线程错误: {e}')
            _cdn_monitor_stop_event.wait(timeout=1)

    logger.info('CDN缓存监控线程已停止')


def start_cdn_monitor():
    """启动CDN监控线程"""
    global _cdn_monitor_thread, _cdn_monitor_running

    cdn_enabled, monitor_enabled, cdn_domain, _api_token, _zone_id, _cache_warming = _get_effective_cdn_settings()
    if not cdn_enabled or not cdn_domain or not monitor_enabled:
        logger.info('CDN监控未启用')
        return

    if _cdn_monitor_thread and _cdn_monitor_thread.is_alive():
        logger.warning('CDN监控线程已在运行')
        return

    _cdn_monitor_running = True
    _cdn_monitor_stop_event.clear()
    _cdn_monitor_thread = threading.Thread(target=_cdn_cache_monitor_worker, daemon=True)
    _cdn_monitor_thread.start()
    logger.info('CDN监控已启动')

    # 恢复未完成的监控任务
    _restore_cdn_monitor_tasks()


def stop_cdn_monitor():
    """停止CDN监控线程"""
    global _cdn_monitor_running, _cdn_monitor_thread

    if not _cdn_monitor_thread:
        return

    logger.info('正在停止CDN监控...')
    _cdn_monitor_running = False
    _cdn_monitor_stop_event.set()

    try:
        cdn_monitor_queue.put((0, next(_cdn_monitor_seq), None), block=False)
    except Exception:
        pass

    if _cdn_monitor_thread.is_alive():
        _cdn_monitor_thread.join(timeout=10)

    logger.info('CDN监控已停止')


def add_to_cdn_monitor(encrypted_id: str, upload_time: Optional[int] = None, delay_seconds: int = 0):
    """添加图片到CDN监控队列"""
    # 必须同时满足：CDN启用、CDN域名配置、监控启用
    cdn_enabled, monitor_enabled, cdn_domain, _api_token, _zone_id, _cache_warming = _get_effective_cdn_settings()
    if not cdn_enabled or not monitor_enabled or not cdn_domain:
        return

    task = {
        'encrypted_id': encrypted_id,
        'upload_time': upload_time or int(time.time()),
        'retries': 0
    }

    try:
        run_at = time.time() + max(0, int(delay_seconds))
        cdn_monitor_queue.put((run_at, next(_cdn_monitor_seq), task), block=False)
        logger.info(f'图片 {encrypted_id} 已加入CDN监控队列')
    except queue.Full:
        logger.warning(f'CDN监控队列已满，无法添加 {encrypted_id}')


def _restore_cdn_monitor_tasks():
    """恢复未完成的CDN监控任务"""
    try:
        # 查找未缓存的近期图片（24小时内）
        since_timestamp = int(time.time()) - 86400
        rows = get_uncached_files(since_timestamp, limit=100)

        if rows:
            logger.info(f'恢复 {len(rows)} 个CDN监控任务')
            for row in rows:
                add_to_cdn_monitor(row['encrypted_id'], row['upload_time'], delay_seconds=0)

    except Exception as e:
        logger.error(f'恢复CDN监控任务失败: {e}')


def get_monitor_queue_size() -> int:
    """获取监控队列大小"""
    _cdn_enabled, monitor_enabled, _cdn_domain, _api_token, _zone_id, _cache_warming = _get_effective_cdn_settings()
    return cdn_monitor_queue.qsize() if monitor_enabled else 0


__all__ = [
    'CloudflareCDN', 'cloudflare_cdn', 'CDNProbeResult',
    'cdn_monitor_queue', 'start_cdn_monitor', 'stop_cdn_monitor',
    'add_to_cdn_monitor', 'get_monitor_queue_size',
]
