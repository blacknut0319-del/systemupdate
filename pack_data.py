"""_decrypted.py → data.txt (AES-GCM, ddong_loader.py와 동일)."""
import base64
import os
import zlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_decrypted.py")
DST = os.path.join(ROOT, "data.txt")


def main():
    with open(SRC, encoding="utf-8") as f:
        code = f.read()
    raw = zlib.compress(code.encode("utf-8"))
    nonce = os.urandom(12)
    enc = AESGCM(KEY).encrypt(nonce, raw, None)
    b64 = base64.b64encode(nonce + enc).decode("ascii")
    with open(DST, "w", encoding="utf-8") as f:
        f.write(b64)
    print(f"OK {DST} ({len(b64)//1024}KB)")


if __name__ == "__main__":
    main()
