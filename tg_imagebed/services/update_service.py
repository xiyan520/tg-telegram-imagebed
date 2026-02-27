#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用更新服务（GitHub Release Artifact 热更新）

设计目标：
- 固定官方 Release 仓库（白名单）
- 支持检查更新 / 异步执行更新 / 状态查询
- 强制 SHA256 校验，防止包被篡改
- 仅覆盖白名单路径，更新失败自动回滚
- 更新成功后自动重启进程
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from .. import __version__
from ..config import BASE_DIR, logger
from ..database import get_system_setting, update_system_settings

OFFICIAL_RELEASE_REPO = 'xiyan520/tg-telegram-imagebed'
OFFICIAL_REPO_URL = f'https://github.com/{OFFICIAL_RELEASE_REPO}.git'
DEFAULT_ASSET_NAME = 'tg-imagebed-release.zip'
DEFAULT_SHA_NAME = 'tg-imagebed-release.zip.sha256'

_RELEASE_API_URL = 'https://api.github.com/repos/{repo}/releases/latest'
_REQUEST_HEADERS = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'tg-telegram-imagebed-updater',
}
_SHA256_RE = re.compile(r'^[a-fA-F0-9]{64}$')
_SEMVER_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')
_MAX_LOG_LINES = 200

_TARGET_REL_PATHS = (
    'VERSION',
    'main.py',
    'requirements.txt',
    'tg_imagebed',
    'frontend/.output/public',
)


# 全局状态
_state_lock = threading.Lock()
_update_thread: threading.Thread | None = None
_restart_thread: threading.Thread | None = None
_state: Dict[str, Any] = {
    'task_id': '',
    'state': 'idle',  # idle|running|downloading|verifying|applying|success|failed|rolling_back|rolled_back|restarting
    'message': '',
    'error': '',
    'started_at': '',
    'finished_at': '',
    'before_version': '',
    'target_version': '',
    'current_version': '',
    # 兼容旧字段（前端历史版本仍可能读取）
    'before_commit': '',
    'target_commit': '',
    'current_commit': '',
    'duration_ms': 0,
    'logs': [],
}


def _normalize_release_repo(value: str) -> str:
    text = (value or '').strip()
    if not text:
        return ''
    if text.startswith('git@github.com:'):
        text = text.replace('git@github.com:', 'https://github.com/', 1)
    text = text.replace('http://github.com/', 'https://github.com/')
    if text.startswith('https://github.com/'):
        text = text[len('https://github.com/'):]
    if text.endswith('/'):
        text = text[:-1]
    if text.lower().endswith('.git'):
        text = text[:-4]
    return text.lower().strip('/')


def _configured_update_source() -> str:
    source = (get_system_setting('app_update_source') or 'release').strip().lower()
    return source or 'release'


def _configured_release_repo() -> str:
    value = (get_system_setting('app_update_release_repo') or '').strip() or OFFICIAL_RELEASE_REPO
    normalized = _normalize_release_repo(value)
    return normalized or OFFICIAL_RELEASE_REPO


def _configured_asset_name() -> str:
    value = (get_system_setting('app_update_release_asset_name') or '').strip() or DEFAULT_ASSET_NAME
    return value


def _configured_sha_name() -> str:
    value = (get_system_setting('app_update_release_sha_name') or '').strip() or DEFAULT_SHA_NAME
    return value


def _release_repo_allowed(repo: str) -> bool:
    return _normalize_release_repo(repo) == _normalize_release_repo(OFFICIAL_RELEASE_REPO)


def _state_copy() -> Dict[str, Any]:
    with _state_lock:
        data = dict(_state)
        data['logs'] = list(_state.get('logs') or [])
    return data


def _append_log(message: str) -> None:
    now = datetime.now().strftime('%H:%M:%S')
    line = f'[{now}] {message}'
    with _state_lock:
        logs = list(_state.get('logs') or [])
        logs.append(line)
        _state['logs'] = logs[-_MAX_LOG_LINES:]
    logger.info(f'[Update] {message}')


def _persist_last_state() -> None:
    data = _state_copy()
    current_version = str(data.get('current_version') or '')
    try:
        update_system_settings({
            'app_update_last_status': str(data.get('state') or 'idle'),
            'app_update_last_error': str(data.get('error') or ''),
            'app_update_last_version': current_version,
            # 兼容旧字段：沿用 current_commit 存版本号
            'app_update_last_commit': current_version,
            'app_update_last_run_at': str(data.get('finished_at') or data.get('started_at') or ''),
            'app_update_last_duration_ms': str(int(data.get('duration_ms') or 0)),
        })
    except Exception as e:
        logger.error(f'持久化更新状态失败: {e}')


def _set_state(**updates: Any) -> None:
    with _state_lock:
        _state.update(updates)
    if 'state' in updates or 'error' in updates or 'finished_at' in updates:
        _persist_last_state()


def _run_cmd(args: List[str], *, cwd: Path, timeout: int = 1800) -> str:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        timeout=timeout,
        check=False,
    )
    stdout = (proc.stdout or '').strip()
    stderr = (proc.stderr or '').strip()
    if proc.returncode != 0:
        detail = stderr or stdout or f'命令失败: {" ".join(args)}'
        raise RuntimeError(detail[:1200])
    return stdout


def _check_pip_available() -> bool:
    try:
        proc = subprocess.run(
            [sys.executable, '-m', 'pip', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            timeout=15,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _repo_path() -> Path:
    return Path(BASE_DIR).resolve()


def _version_file() -> Path:
    return _repo_path() / 'VERSION'


def _current_version() -> str:
    version_path = _version_file()
    if version_path.exists():
        return version_path.read_text(encoding='utf-8').strip()
    return __version__


def _parse_semver(value: str) -> Tuple[int, int, int]:
    text = (value or '').strip()
    match = _SEMVER_RE.match(text)
    if not match:
        raise RuntimeError(f'非法版本号: {value}')
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _normalize_release_version(value: str) -> str:
    text = (value or '').strip()
    if text.startswith('v'):
        text = text[1:]
    return text


def _is_newer_version(current: str, latest: str) -> bool:
    return _parse_semver(latest) > _parse_semver(current)


def _github_get_json(url: str) -> Dict[str, Any]:
    try:
        response = requests.get(url, headers=_REQUEST_HEADERS, timeout=30)
    except Exception as e:
        raise RuntimeError(f'请求 GitHub 失败: {e}') from e
    if response.status_code >= 400:
        if response.status_code == 404:
            raise RuntimeError('未找到可用 Release，请先创建正式发布版本')
        detail = (response.text or '').strip()
        raise RuntimeError(f'GitHub API 返回异常（{response.status_code}）: {detail[:300]}')
    try:
        return response.json()
    except Exception as e:
        raise RuntimeError(f'GitHub API 响应解析失败: {e}') from e


def _fetch_latest_release(repo: str) -> Dict[str, Any]:
    api_url = _RELEASE_API_URL.format(repo=repo)
    payload = _github_get_json(api_url)
    assets_raw = payload.get('assets') or []
    assets: Dict[str, Dict[str, Any]] = {}
    for item in assets_raw:
        name = str(item.get('name') or '').strip()
        if not name:
            continue
        assets[name] = {
            'name': name,
            'url': str(item.get('browser_download_url') or '').strip(),
            'size': int(item.get('size') or 0),
        }
    tag_name = str(payload.get('tag_name') or '').strip()
    if not tag_name:
        raise RuntimeError('Release 缺少 tag_name')
    latest_version = _normalize_release_version(tag_name)
    _parse_semver(latest_version)
    return {
        'tag_name': tag_name,
        'latest_version': latest_version,
        'name': str(payload.get('name') or '').strip(),
        'published_at': str(payload.get('published_at') or '').strip(),
        'prerelease': bool(payload.get('prerelease')),
        'assets': assets,
    }


def _download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, headers=_REQUEST_HEADERS, stream=True, timeout=120) as response:
            if response.status_code >= 400:
                detail = (response.text or '').strip()
                raise RuntimeError(f'下载失败（{response.status_code}）: {detail[:300]}')
            with open(target, 'wb') as fp:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        fp.write(chunk)
    except Exception as e:
        raise RuntimeError(f'下载文件失败: {e}') from e


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fp:
        while True:
            block = fp.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _read_expected_sha256(path: Path) -> str:
    raw = path.read_text(encoding='utf-8').strip()
    for line in raw.splitlines():
        tokens = [tok.strip() for tok in line.strip().split(' ') if tok.strip()]
        for token in tokens:
            if _SHA256_RE.fullmatch(token):
                return token.lower()
    raise RuntimeError('SHA256 文件格式无效，未找到合法摘要')


def _safe_extract_zip(zip_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            entry = member.filename
            entry_path = Path(entry)
            if entry_path.is_absolute() or '..' in entry_path.parts:
                raise RuntimeError(f'压缩包包含非法路径: {entry}')
        zf.extractall(target_dir)


def _resolve_release_root(staging_dir: Path) -> Path:
    children = [p for p in staging_dir.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        candidate = children[0]
        if (candidate / 'VERSION').exists():
            return candidate
    return staging_dir


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
    else:
        path.unlink()


def _copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _backup_targets(repo_path: Path, backup_dir: Path) -> List[Tuple[str, bool]]:
    manifest: List[Tuple[str, bool]] = []
    backup_dir.mkdir(parents=True, exist_ok=True)
    for rel in _TARGET_REL_PATHS:
        rel_path = Path(rel)
        target = repo_path / rel_path
        existed = target.exists()
        manifest.append((str(rel_path), existed))
        if existed:
            backup_target = backup_dir / rel_path
            if backup_target.exists():
                _remove_path(backup_target)
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            _copy_path(target, backup_target)
    return manifest


def _apply_release(staging_root: Path, repo_path: Path) -> None:
    for rel in _TARGET_REL_PATHS:
        rel_path = Path(rel)
        source = staging_root / rel_path
        if not source.exists():
            raise RuntimeError(f'Release 包缺少必要路径: {rel}')
        target = repo_path / rel_path
        if target.exists():
            _remove_path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        _copy_path(source, target)


def _rollback_from_backup(repo_path: Path, backup_dir: Path, manifest: List[Tuple[str, bool]]) -> None:
    for rel, existed in manifest:
        rel_path = Path(rel)
        target = repo_path / rel_path
        backup = backup_dir / rel_path
        if target.exists():
            _remove_path(target)
        if existed:
            if not backup.exists():
                raise RuntimeError(f'回滚缺少备份文件: {rel}')
            target.parent.mkdir(parents=True, exist_ok=True)
            _copy_path(backup, target)


def _install_dependencies() -> None:
    repo_path = _repo_path()
    if not _check_pip_available():
        raise RuntimeError('未检测到 pip，无法同步 Python 依赖')
    _append_log('同步 Python 依赖...')
    _run_cmd([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], cwd=repo_path, timeout=1800)


def _restart_process() -> None:
    python_bin = sys.executable
    main_py = _repo_path() / 'main.py'
    if not main_py.exists():
        raise RuntimeError(f'未找到启动文件: {main_py}')

    _append_log('准备重启服务进程...')
    os.chdir(str(_repo_path()))
    os.execv(python_bin, [python_bin, str(main_py)])


def _schedule_restart(task_id: str) -> None:
    def runner() -> None:
        try:
            time.sleep(1.5)
            status = _state_copy()
            if status.get('task_id') != task_id or status.get('state') != 'success':
                return
            _set_state(state='restarting', message='更新完成，正在重启服务...')
            _append_log('更新完成，开始自动重启...')
            _restart_process()
        except Exception as e:
            _append_log(f'自动重启失败: {e}')
            _set_state(state='failed', error=f'自动重启失败: {e}', message='更新成功但自动重启失败')

    global _restart_thread
    _restart_thread = threading.Thread(target=runner, daemon=True, name='app-update-restart')
    _restart_thread.start()


def get_update_runtime_info() -> Dict[str, Any]:
    repo_path = _repo_path()
    release_repo = _configured_release_repo()
    asset_name = _configured_asset_name()
    sha_name = _configured_sha_name()
    update_source = _configured_update_source()
    pip_available = _check_pip_available()
    current_version = _current_version()
    repo_allowed = _release_repo_allowed(release_repo)
    release_supported = update_source == 'release' and repo_allowed

    # 兼容旧前端字段：Git 链路已停用
    git_available = shutil.which('git') is not None
    node_available = shutil.which('node') is not None
    npm_available = shutil.which('npm') is not None

    return {
        'app_version': __version__,
        'current_version': current_version,
        'current_commit': current_version,  # 兼容旧字段
        'repo_path': str(repo_path),
        'update_source': update_source,
        'release_repo': release_repo,
        'release_repo_url': OFFICIAL_REPO_URL,
        'release_asset_name': asset_name,
        'release_sha_name': sha_name,
        'release_supported': release_supported,
        'repo_allowed': repo_allowed,
        'pip_available': pip_available,
        # 兼容旧字段
        'git_available': git_available,
        'node_available': node_available,
        'npm_available': npm_available,
        'is_git_repo': False,
        'repo_clean': True,
        'repo_url': OFFICIAL_REPO_URL,
        'branch': 'release',
    }


def check_for_updates() -> Dict[str, Any]:
    info = get_update_runtime_info()
    if info['update_source'] != 'release':
        raise RuntimeError('当前环境仅支持 Release 更新模式')
    if not info['repo_allowed']:
        raise RuntimeError('更新源未通过白名单校验，仅允许官方仓库')

    release = _fetch_latest_release(info['release_repo'])
    assets = release['assets']
    asset_name = info['release_asset_name']
    sha_name = info['release_sha_name']
    asset = assets.get(asset_name)
    sha_asset = assets.get(sha_name)

    current_version = str(info['current_version'] or __version__)
    latest_version = str(release['latest_version'])
    has_update = _is_newer_version(current_version, latest_version)

    return {
        'current_version': current_version,
        'latest_version': latest_version,
        'has_update': has_update,
        'release_tag': release['tag_name'],
        'release_name': release['name'],
        'published_at': release['published_at'],
        'asset_found': bool(asset and asset.get('url')),
        'sha_found': bool(sha_asset and sha_asset.get('url')),
        'asset_name': asset_name,
        'sha_name': sha_name,
        'asset_url': (asset or {}).get('url', ''),
        'sha_url': (sha_asset or {}).get('url', ''),
        # 兼容旧字段
        'current_commit': current_version,
        'remote_commit': latest_version,
        'behind_count': 1 if has_update else 0,
    }


def _execute_update_task(task_id: str) -> None:
    started_ts = time.time()
    repo_path = _repo_path()
    data_dir = repo_path / 'data' / 'app_update'
    tmp_dir = data_dir / 'tmp' / task_id
    backup_dir = data_dir / 'backups' / task_id
    downloads_dir = tmp_dir / 'downloads'
    staging_dir = tmp_dir / 'staging'
    manifest: List[Tuple[str, bool]] = []
    before_version = ''

    try:
        info = get_update_runtime_info()
        if not info['release_supported']:
            raise RuntimeError('当前环境不支持 Release 热更新')
        if not info['pip_available']:
            raise RuntimeError('未检测到 pip，无法执行更新')

        check = check_for_updates()
        before_version = str(check['current_version'] or '')
        _set_state(
            before_version=before_version,
            current_version=before_version,
            before_commit=before_version,
            current_commit=before_version,
        )
        _append_log(f'当前版本: {before_version or "unknown"}')

        if not check['has_update']:
            _append_log('远端无新版本，当前已是最新版本')
            duration_ms = int((time.time() - started_ts) * 1000)
            _set_state(
                state='success',
                message='当前已是最新版本，无需更新',
                finished_at=datetime.now().isoformat(timespec='seconds'),
                duration_ms=duration_ms,
                target_version=before_version,
                target_commit=before_version,
                error='',
            )
            return

        if not check['asset_found']:
            raise RuntimeError(f'Release 缺少更新包: {check["asset_name"]}')
        if not check['sha_found']:
            raise RuntimeError(f'Release 缺少校验文件: {check["sha_name"]}')

        target_version = str(check['latest_version'] or '')
        _set_state(target_version=target_version, target_commit=target_version)
        _append_log(f'检测到新版本: {target_version}（tag: {check["release_tag"]}）')

        downloads_dir.mkdir(parents=True, exist_ok=True)
        staging_dir.mkdir(parents=True, exist_ok=True)

        asset_path = downloads_dir / check['asset_name']
        sha_path = downloads_dir / check['sha_name']

        _set_state(state='downloading', message='正在下载 Release 资产...')
        _append_log(f'下载更新包: {check["asset_name"]}')
        _download_file(str(check['asset_url']), asset_path)
        _append_log(f'下载校验文件: {check["sha_name"]}')
        _download_file(str(check['sha_url']), sha_path)

        _set_state(state='verifying', message='正在校验更新包完整性...')
        expected_sha = _read_expected_sha256(sha_path)
        actual_sha = _sha256_of_file(asset_path)
        if expected_sha != actual_sha:
            raise RuntimeError(f'SHA256 校验失败: expected={expected_sha}, actual={actual_sha}')
        _append_log('SHA256 校验通过')

        _append_log('解压更新包...')
        _safe_extract_zip(asset_path, staging_dir)
        release_root = _resolve_release_root(staging_dir)
        for rel in _TARGET_REL_PATHS:
            if not (release_root / rel).exists():
                raise RuntimeError(f'更新包缺少必要文件: {rel}')

        _set_state(state='applying', message='正在应用更新...')
        _append_log('备份当前文件...')
        manifest = _backup_targets(repo_path, backup_dir)

        _append_log('覆盖应用文件...')
        _apply_release(release_root, repo_path)

        _install_dependencies()

        current_version = _current_version()
        duration_ms = int((time.time() - started_ts) * 1000)
        _append_log(f'更新完成，当前版本: {current_version}')
        _set_state(
            state='success',
            message='更新成功，正在准备重启',
            finished_at=datetime.now().isoformat(timespec='seconds'),
            duration_ms=duration_ms,
            current_version=current_version,
            current_commit=current_version,
            error='',
        )
        _schedule_restart(task_id)
    except Exception as e:
        err = str(e)
        _append_log(f'更新失败: {err}')
        rollback_error = ''

        if manifest:
            _set_state(state='rolling_back', message='更新失败，正在回滚', error=err)
            try:
                _append_log('回滚到更新前版本...')
                _rollback_from_backup(repo_path, backup_dir, manifest)
                _install_dependencies()
                rolled_version = _current_version()
                duration_ms = int((time.time() - started_ts) * 1000)
                _append_log(f'回滚成功，当前版本: {rolled_version}')
                _set_state(
                    state='rolled_back',
                    message='更新失败，已自动回滚到上一版本',
                    finished_at=datetime.now().isoformat(timespec='seconds'),
                    duration_ms=duration_ms,
                    current_version=rolled_version,
                    current_commit=rolled_version,
                    error=err,
                )
            except Exception as re_error:
                rollback_error = str(re_error)
        else:
            duration_ms = int((time.time() - started_ts) * 1000)
            _set_state(
                state='failed',
                message='更新失败',
                finished_at=datetime.now().isoformat(timespec='seconds'),
                duration_ms=duration_ms,
                current_version=before_version,
                current_commit=before_version,
                error=err,
            )

        if rollback_error:
            duration_ms = int((time.time() - started_ts) * 1000)
            final_error = f'{err}; 回滚失败: {rollback_error}'
            _append_log(f'回滚失败: {rollback_error}')
            _set_state(
                state='failed',
                message='更新失败且回滚失败，请手动处理',
                finished_at=datetime.now().isoformat(timespec='seconds'),
                duration_ms=duration_ms,
                error=final_error,
            )
    finally:
        try:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

        global _update_thread
        with _state_lock:
            _update_thread = None


def start_update_task() -> Tuple[bool, str, str]:
    global _update_thread
    with _state_lock:
        busy = _update_thread is not None and _update_thread.is_alive()
        if busy or _state.get('state') in {'running', 'downloading', 'verifying', 'applying', 'restarting', 'rolling_back'}:
            return False, '已有更新任务正在执行，请稍后再试', str(_state.get('task_id') or '')

        task_id = datetime.now().strftime('%Y%m%d%H%M%S')
        _state.update({
            'task_id': task_id,
            'state': 'running',
            'message': '更新任务已启动',
            'error': '',
            'started_at': datetime.now().isoformat(timespec='seconds'),
            'finished_at': '',
            'before_version': '',
            'target_version': '',
            'current_version': '',
            'before_commit': '',
            'target_commit': '',
            'current_commit': '',
            'duration_ms': 0,
            'logs': [],
        })
    _persist_last_state()
    _append_log('开始执行 Release 热更新任务')

    _update_thread = threading.Thread(
        target=_execute_update_task,
        args=(task_id,),
        daemon=True,
        name='app-update-worker',
    )
    _update_thread.start()
    return True, '更新任务已启动', task_id


def get_update_status() -> Dict[str, Any]:
    data = _state_copy()
    try:
        info = get_update_runtime_info()
        if not data.get('current_version'):
            data['current_version'] = info.get('current_version') or ''
        if not data.get('current_commit'):
            data['current_commit'] = data.get('current_version') or ''
        data['runtime'] = info
    except Exception:
        data['runtime'] = {}
    return data
