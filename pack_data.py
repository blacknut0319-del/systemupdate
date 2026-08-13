"""_decrypted.py → data.txt (AES-GCM) + version.txt 동기화.

PATCH_UPDATED_AT 은 실행 시점(로컬 시각)으로 자동 갱신.
pre-commit 훅에서 커밋 직전에 호출하면 커밋 완료 시각과 일치.
"""
import base64
import os
import re
import zlib
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = base64.b64decode("W5EwW1vV8EFoNKQsgTCrKmfZzbflm0JDU7MuNG8izu4=")
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_decrypted.py")
DST = os.path.join(ROOT, "data.txt")
VER = os.path.join(ROOT, "version.txt")
ATTACKER_SRC = os.path.join(ROOT, "attacker_hp.pyw")
ATTACKER_VER = os.path.join(ROOT, "attacker_version.txt")
_PATCH_RE = re.compile(r'(PATCH_UPDATED_AT\s*=\s*")[^"]+(")')


def stamp_patch_time(paths):
    """소스의 PATCH_UPDATED_AT 을 현재 로컬 시각(분 단위)으로 맞춤."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        new_text, n = _PATCH_RE.subn(rf'\g<1>{now}\g<2>', text, count=1)
        if n:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
    return now


def main():
    stamp_patch_time([SRC, ATTACKER_SRC])
    with open(SRC, encoding="utf-8") as f:
        code = f.read()
    raw = zlib.compress(code.encode("utf-8"))
    nonce = os.urandom(12)
    enc = AESGCM(KEY).encrypt(nonce, raw, None)
    b64 = base64.b64encode(nonce + enc).decode("ascii")
    with open(DST, "w", encoding="utf-8") as f:
        f.write(b64)
    m = re.search(r'PATCH_UPDATED_AT\s*=\s*"([^"]+)"', code)
    if m:
        with open(VER, "w", encoding="utf-8") as f:
            f.write(m.group(1).strip() + "\n")
        print(f"완료 {DST} ({len(b64)//1024}KB) / version.txt={m.group(1).strip()}")
    else:
        print(f"완료 {DST} ({len(b64)//1024}KB) — PATCH_UPDATED_AT 없음")
    if os.path.isfile(ATTACKER_SRC):
        with open(ATTACKER_SRC, encoding="utf-8") as f:
            acode = f.read()
        am = re.search(r'PATCH_UPDATED_AT\s*=\s*"([^"]+)"', acode)
        if am:
            with open(ATTACKER_VER, "w", encoding="utf-8") as f:
                f.write(am.group(1).strip() + "\n")
            print(f"attacker_version.txt={am.group(1).strip()}")


if __name__ == "__main__":
    main()
