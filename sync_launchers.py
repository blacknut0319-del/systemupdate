# -*- coding: utf-8 -*-
"""pythonw.exe 복사본 → sooplive client.exe / sooplive service.exe (작업관리자 프로세스명용)."""
import os
import shutil
import sys

CLIENT = "sooplive client.exe"
SERVICE = "sooplive service.exe"


def _pythonw_source():
    exe = os.path.abspath(sys.executable)
    base = os.path.basename(exe).lower()
    if base in ("pythonw.exe", "python.exe"):
        pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
        return pyw if os.path.isfile(pyw) else exe
    if base.endswith(".exe"):
        return exe
    return exe


def sync_launcher(name, app_dir=None):
    app_dir = app_dir or os.path.dirname(os.path.abspath(__file__))
    dst = os.path.join(app_dir, name)
    src = _pythonw_source()
    if not os.path.isfile(src):
        return dst
    try:
        shutil.copy2(src, dst)
    except Exception:
        pass
    return dst


def sync_all(app_dir=None):
    app_dir = app_dir or os.path.dirname(os.path.abspath(__file__))
    sync_launcher(CLIENT, app_dir)
    sync_launcher(SERVICE, app_dir)
    return app_dir


if __name__ == "__main__":
    ad = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    sync_all(ad)
    print("ok", ad)
