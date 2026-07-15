"""GitHub data.txt 가 최신 _decrypted 와 맞는지 확인."""
import base64
import json
import ssl
import urllib.request
import zlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
API = "https://api.github.com/repos/blacknut0319-del/systemupdate/contents/data.txt?ref=main"
RAW = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/data.txt"


def fetch_code(use_api=True):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if use_api:
        req = urllib.request.Request(API, headers={"User-Agent": "ddong-verify"})
        meta = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
        b64 = base64.b64decode(meta["content"])
    else:
        req = urllib.request.Request(
            RAW,
            headers={"User-Agent": "ddong-verify", "Cache-Control": "no-cache", "Pragma": "no-cache"},
        )
        b64 = urllib.request.urlopen(req, timeout=20, context=ctx).read()
    raw = base64.b64decode(b64)
    g = AESGCM(KEY)
    return zlib.decompress(g.decrypt(raw[:12], raw[12:], None)).decode("utf-8")


if __name__ == "__main__":
    for label, api in (("API", True), ("RAW_CDN", False)):
        code = fetch_code(api)
        stamp = ""
        i = code.find('PATCH_UPDATED_AT = "')
        if i >= 0:
            stamp = code[i : i + 40]
        print(f"[{label}] stamp={stamp} f0f0f0={'f0f0f0' in code}")
