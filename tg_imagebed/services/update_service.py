#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用更新服务（GitHub 源码热更新）

设计目标：
- 仅允许固定官方仓库
- 支持检查更新 / 异步执行更新 / 状态查询
- 更新失败自动回滚
- 更新成功后自动重启进程
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

from .. import __version__
from ..config import BASE_DIR, logger
from ..database import get_system_setting, update_system_settings

# 固定更新源（白名单）
OFFICIAL_REPO_URL = 'https://github.com/xiyan520/tg-telegram-imagebed.git'
ALLOWED_BRANCHES = {'main', 'master'}

# 全局状态
_state_lock = threading.Lock()
_update_thread: threading.Thread | None = None
_restart_thread: threading.Thread | None = None
_state: Dict[str, Any] = {
    'task_id': '',
    'state': 'idle',  # idle|running|success|failed|rolling_back|rolled_back|restarting
    'message': '',
    'error': '',
    'started_at': '',
    'finished_at': '',
    'before_commit': '',
    'target_commit': '',
    'current_commit': '',
    'duration_ms': 0,
    'logs': [],
}


def _normalize_repo_url(url: str) -> str:
    """规范化仓库 URL，用于白名单校验"""
    value = (url or '').strip()
    if not value:
        return ''

    # 支持 git@github.com:owner/repo.git 的形式
    if value.startswith('git@github.com:'):
        value = value.replace('git@github.com:', 'https://github.com/', 1)

    if value.endswith('/'):
        value = value[:-1]
    if value.lower().endswith('.git'):
        value = value[:-4]
    return value.lower()


def _official_repo_normalized() -> str:
    return _normalize_repo_url(OFFICIAL_REPO_URL)


def _configured_repo_url() -> str:
    repo = (get_system_setting('app_update_repo_url') or '').strip() or OFFICIAL_REPO_URL
    return repo


def _configured_branch() -> str:
    branch = (get_system_setting('app_update_branch') or '').strip().lower() or 'main'
    if branch not in ALLOWED_BRANCHES:
        return 'main'
    return branch


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
        _state['logs'] = logs[-200:]
    logger.info(f"[Update] {message}")


def _persist_last_state() -> None:
    """持久化最近状态，保证重启后可见"""
    data = _state_copy()
    try:
        update_system_settings({
            'app_update_last_status': str(data.get('state') or 'idle'),
            'app_update_last_error': str(data.get('error') or ''),
            'app_update_last_commit': str(data.get('current_commit') or ''),
            'app_update_last_run_at': str(data.get('finished_at') or data.get('started_at') or ''),
            'app_update_last_duration_ms': str(int(data.get('duration_ms') or 0)),
        })
    except Exception as e:
        logger.error(f"持久化更新状态失败: {e}")


def _set_state(**updates: Any) -> None:
    with _state_lock:
        _state.update(updates)
    if 'state' in updates or 'error' in updates or 'finished_at' in updates:
        _persist_last_state()


def _ensure_repo_allowed(repo_url: str) -> None:
    if _normalize_repo_url(repo_url) != _official_repo_normalized():
        raise RuntimeError('更新源未通过白名单校验，仅允许官方仓库')


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


def _has_binary(name: str) -> bool:
    return shutil.which(name) is not None


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


def _frontend_path() -> Path:
    return _repo_path() / 'frontend'


def _is_git_repo(path: Path) -> bool:
    return (path / '.git').exists()


def _git_current_commit(path: Path) -> str:
    return _run_cmd(['git', 'rev-parse', '--short', 'HEAD'], cwd=path, timeout=30)


def _git_current_branch(path: Path) -> str:
    return _run_cmd(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=path, timeout=30)


def _git_is_clean(path: Path) -> bool:
    out = _run_cmd(['git', 'status', '--porcelain'], cwd=path, timeout=30)
    return out.strip() == ''


def get_update_runtime_info() -> Dict[str, Any]:
    repo_path = _repo_path()
    git_available = _has_binary('git')
    node_available = _has_binary('node')
    npm_available = _has_binary('npm')
    pip_available = _check_pip_available()
    is_repo = _is_git_repo(repo_path)

    current_commit = ''
    current_branch = ''
    repo_clean = False
    git_error = ''

    if git_available and is_repo:
        try:
            current_commit = _git_current_commit(repo_path)
            current_branch = _git_current_branch(repo_path)
            repo_clean = _git_is_clean(repo_path)
        except Exception as e:
            git_error = str(e)

    repo_url = _configured_repo_url()
    branch = _configured_branch()
    repo_allowed = _normalize_repo_url(repo_url) == _official_repo_normalized()

    return {
        'app_version': __version__,
        'repo_path': str(repo_path),
        'frontend_path': str(_frontend_path()),
        'git_available': git_available,
        'node_available': node_available,
        'npm_available': npm_available,
        'pip_available': pip_available,
        'is_git_repo': is_repo,
        'repo_clean': repo_clean,
        'current_commit': current_commit,
        'current_branch': current_branch,
        'git_error': git_error,
        'repo_url': repo_url,
        'branch': branch,
        'repo_allowed': repo_allowed,
    }


def check_for_updates() -> Dict[str, Any]:
    repo_path = _repo_path()
    info = get_update_runtime_info()

    if not info['git_available']:
        raise RuntimeError('未检测到 git，当前环境不支持源码热更新')
    if not info['is_git_repo']:
        raise RuntimeError('当前运行目录不是 Git 仓库，无法执行源码热更新')
    if not info['repo_allowed']:
        raise RuntimeError('更新源未通过白名单校验，仅允许官方仓库')

    repo_url = info['repo_url']
    branch = info['branch']
    _ensure_repo_allowed(repo_url)

    current_commit_full = _run_cmd(['git', 'rev-parse', 'HEAD'], cwd=repo_path, timeout=30)
    current_commit = _run_cmd(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo_path, timeout=30)
    _run_cmd(['git', 'fetch', '--depth=1', repo_url, branch], cwd=repo_path, timeout=300)
    remote_commit_full = _run_cmd(['git', 'rev-parse', 'FETCH_HEAD'], cwd=repo_path, timeout=30)
    remote_commit = _run_cmd(['git', 'rev-parse', '--short', 'FETCH_HEAD'], cwd=repo_path, timeout=30)
    behind_count_text = _run_cmd(['git', 'rev-list', '--count', f'{current_commit_full}..{remote_commit_full}'], cwd=repo_path, timeout=30)
    behind_count = int(behind_count_text or '0')

    return {
        'current_commit': current_commit,
        'remote_commit': remote_commit,
        'behind_count': behind_count,
        'has_update': behind_count > 0,
        'branch': branch,
        'repo_url': repo_url,
    }


def _install_dependencies() -> None:
    repo_path = _repo_path()
    frontend_path = _frontend_path()

    if not _check_pip_available():
        raise RuntimeError('未检测到 pip，无法同步 Python 依赖')
    if not _has_binary('npm'):
        raise RuntimeError('未检测到 npm，无法构建前端')

    _append_log('同步 Python 依赖...')
    _run_cmd([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], cwd=repo_path, timeout=1800)

    if not frontend_path.exists():
        raise RuntimeError('未找到 frontend 目录，无法构建前端')

    _append_log('安装前端依赖（npm ci）...')
    try:
        _run_cmd(['npm', 'ci', '--prefix', str(frontend_path)], cwd=repo_path, timeout=1800)
    except Exception as npm_ci_error:
        _append_log(f'npm ci 失败，尝试 npm install 兜底: {npm_ci_error}')
        _run_cmd(['npm', 'install', '--prefix', str(frontend_path)], cwd=repo_path, timeout=1800)

    _append_log('构建前端静态产物（npm run generate）...')
    _run_cmd(['npm', 'run', 'generate', '--prefix', str(frontend_path)], cwd=repo_path, timeout=2400)


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


def _execute_update_task(task_id: str) -> None:
    started_ts = time.time()
    repo_path = _repo_path()
    before_commit_full = ''
    before_commit_short = ''

    try:
        info = get_update_runtime_info()
        if not info['git_available']:
            raise RuntimeError('未检测到 git，当前环境不支持源码热更新')
        if not info['is_git_repo']:
            raise RuntimeError('当前运行目录不是 Git 仓库，无法执行源码热更新')
        if not info['repo_allowed']:
            raise RuntimeError('更新源未通过白名单校验，仅允许官方仓库')
        if not info['repo_clean']:
            raise RuntimeError('仓库存在未提交改动，请先清理后再执行热更新')
        if not info['node_available'] or not info['npm_available']:
            raise RuntimeError('未检测到 Node.js/npm，无法执行前端热更新构建')
        if not info['pip_available']:
            raise RuntimeError('未检测到 pip，无法同步后端依赖')

        repo_url = info['repo_url']
        branch = info['branch']
        _ensure_repo_allowed(repo_url)

        _append_log(f'校验通过，更新源: {repo_url}，分支: {branch}')
        before_commit_full = _run_cmd(['git', 'rev-parse', 'HEAD'], cwd=repo_path, timeout=30)
        before_commit_short = _run_cmd(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo_path, timeout=30)
        _set_state(before_commit=before_commit_short, current_commit=before_commit_short)
        _append_log(f'当前提交: {before_commit_short}')

        check = check_for_updates()
        if not check['has_update']:
            _append_log('远端无新提交，当前已是最新版本')
            duration_ms = int((time.time() - started_ts) * 1000)
            _set_state(
                state='success',
                message='当前已是最新版本，无需更新',
                finished_at=datetime.now().isoformat(timespec='seconds'),
                duration_ms=duration_ms,
                current_commit=before_commit_short,
                target_commit=before_commit_short,
                error='',
            )
            return

        target_commit = check['remote_commit']
        _set_state(target_commit=target_commit)
        _append_log(f'检测到新版本，目标提交: {target_commit}（落后 {check["behind_count"]} 个提交）')

        _append_log('拉取远端代码并切换到目标提交...')
        _run_cmd(['git', 'fetch', '--depth=1', repo_url, branch], cwd=repo_path, timeout=300)
        _run_cmd(['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=repo_path, timeout=120)

        _install_dependencies()

        current_commit = _run_cmd(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo_path, timeout=30)
        duration_ms = int((time.time() - started_ts) * 1000)
        _append_log(f'更新完成，当前提交: {current_commit}')
        _set_state(
            state='success',
            message='更新成功，正在准备重启',
            finished_at=datetime.now().isoformat(timespec='seconds'),
            duration_ms=duration_ms,
            current_commit=current_commit,
            error='',
        )
        _schedule_restart(task_id)
    except Exception as e:
        err = str(e)
        _append_log(f'更新失败: {err}')
        _set_state(state='rolling_back', message='更新失败，正在回滚', error=err)

        rollback_error = ''
        try:
            if before_commit_full:
                _append_log('回滚到更新前版本...')
                _run_cmd(['git', 'reset', '--hard', before_commit_full], cwd=repo_path, timeout=120)
                _install_dependencies()
                rolled_commit = _run_cmd(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo_path, timeout=30)
                duration_ms = int((time.time() - started_ts) * 1000)
                _append_log(f'回滚成功，当前提交: {rolled_commit}')
                _set_state(
                    state='rolled_back',
                    message='更新失败，已自动回滚到上一版本',
                    finished_at=datetime.now().isoformat(timespec='seconds'),
                    duration_ms=duration_ms,
                    current_commit=rolled_commit,
                    error=err,
                )
            else:
                rollback_error = '缺少更新前提交信息，无法自动回滚'
        except Exception as re:
            rollback_error = str(re)

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
        global _update_thread
        with _state_lock:
            _update_thread = None


def start_update_task() -> Tuple[bool, str, str]:
    global _update_thread
    with _state_lock:
        busy = _update_thread is not None and _update_thread.is_alive()
        if busy or _state.get('state') in {'running', 'restarting', 'rolling_back'}:
            return False, '已有更新任务正在执行，请稍后再试', str(_state.get('task_id') or '')

        task_id = datetime.now().strftime('%Y%m%d%H%M%S')
        _state.update({
            'task_id': task_id,
            'state': 'running',
            'message': '更新任务已启动',
            'error': '',
            'started_at': datetime.now().isoformat(timespec='seconds'),
            'finished_at': '',
            'before_commit': '',
            'target_commit': '',
            'duration_ms': 0,
            'logs': [],
        })
    _persist_last_state()
    _append_log('开始执行热更新任务')

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
    # 兜底：当前提交从 git 读取（可读时）
    try:
        info = get_update_runtime_info()
        if not data.get('current_commit') and info.get('current_commit'):
            data['current_commit'] = info.get('current_commit')
        data['runtime'] = info
    except Exception:
        data['runtime'] = {}
    return data
