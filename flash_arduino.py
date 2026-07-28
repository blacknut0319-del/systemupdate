# -*- coding: utf-8 -*-
"""아두이노 펌웨어 업로드 — Leonardo(ATmega32u4) + 번들 avrdude.
처음에 잘 되던 방식(짧게 대기 후 바로 업로드) + 타임아웃만 추가.
확인(V) 기능과 무관 — hex만 구우면 됨."""
from __future__ import annotations

import os
import ssl
import sys
import time
import tempfile
import threading
import subprocess
import urllib.request

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

HERE = os.path.dirname(os.path.abspath(__file__))
GH_RAW = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main"
HEX_NAME = "뚱힐러.hex"
NEEDED = [
    ("firmware/뚱힐러.hex", HEX_NAME),
    ("firmware/avrdude/avrdude.exe", os.path.join("avrdude", "avrdude.exe")),
    ("firmware/avrdude/avrdude.conf", os.path.join("avrdude", "avrdude.conf")),
    ("firmware/avrdude/libusb0.dll", os.path.join("avrdude", "libusb0.dll")),
]


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def firmware_candidates():
    return [
        os.path.join(HERE, "firmware"),
        os.path.join(os.path.expanduser("~"), "Desktop", "뚱힐러_github", "firmware"),
        os.path.join(tempfile.gettempdir(), "ddong_firmware"),
    ]


def _has_tools(root):
    return (
        os.path.isfile(os.path.join(root, HEX_NAME))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.exe"))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.conf"))
    )


def ensure_firmware(callback=None):
    for root in firmware_candidates():
        if _has_tools(root):
            return root
    root = os.path.join(tempfile.gettempdir(), "ddong_firmware")
    os.makedirs(os.path.join(root, "avrdude"), exist_ok=True)
    ctx = _ssl_ctx()
    for remote, local in NEEDED:
        dest = os.path.join(root, local)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            continue
        if callback:
            callback(5, f"다운로드: {os.path.basename(local)}")
        from urllib.parse import quote
        parts = remote.split("/")
        url = GH_RAW + "/" + "/".join(
            quote(p, safe="") if any(ord(c) > 127 for c in p) else p for p in parts
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ddong"})
            data = urllib.request.urlopen(req, timeout=60, context=ctx).read()
            if len(data) < 1000:
                return None
            with open(dest, "wb") as f:
                f.write(data)
        except Exception:
            return None
    return root if _has_tools(root) else None


def find_arduino_ports():
    """뚱힐러 auto_find_arduino()와 같은 판정."""
    if list_ports is None:
        return []
    ports = list(list_ports.comports())
    found = []

    def _add(dev):
        if dev and dev not in found:
            found.append(dev)

    for p in ports:
        h = (p.hwid or "").upper()
        if "046D" in h and "C08B" in h:
            _add(p.device)
    for p in ports:
        h = (p.hwid or "").upper()
        if "2341" in h or "2A03" in h or "1B4F" in h:
            _add(p.device)
    for p in ports:
        d = f"{p.description or ''} {p.manufacturer or ''}"
        du = d.upper()
        h = (p.hwid or "").lower()
        if (
            "CH340" in du
            or "ARDUINO" in du
            or "LEONARDO" in du
            or "USB" in du
            or "직렬" in d
            or "SERIAL" in du
            or "CP210" in du
            or "vid_2341" in h
            or "vid_2a03" in h
            or "vid_1b4f" in h
        ):
            _add(p.device)
    return found


def find_arduino(preferred=None):
    ports_now = {p.device for p in list_ports.comports()} if list_ports else set()
    if preferred and preferred in ports_now:
        return preferred
    ports = find_arduino_ports()
    return ports[0] if ports else None


def _ports_set():
    if list_ports is None:
        return set()
    return {p.device for p in list_ports.comports()}


def trigger_leonardo_bootloader(port):
    """Leonardo: 1200bps open/close → 부트로더."""
    if serial is None:
        return
    try:
        s = serial.Serial(port, 1200)
        try:
            s.dtr = False
        except Exception:
            pass
        s.close()
    except Exception:
        pass
    # 부트로더 창은 짧음 — 너무 오래 기다리면 이미 끝나서 업로드가 영원히 대기함
    time.sleep(1.2)


def pick_upload_port(preferred, old_ports):
    """새 COM이 떴으면 그걸, 아니면 원래 포트(처음에 성공하던 방식)."""
    now = _ports_set()
    added = [p for p in (now - old_ports) if p]
    if added:
        return added[0]
    if preferred and preferred in now:
        return preferred
    return find_arduino(preferred=preferred) or preferred


def _run_avrdude(cmd, callback=None, timeout_sec=25, pct_write=55, pct_verify=80):
    """avrdude 1회. 응답 없으면 timeout_sec 후 강제 종료(무한대기 방지)."""
    if callback:
        callback(40, "avrdude 업로드 시작...")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception as e:
        return False, str(e), []

    out_lines = []
    t0 = time.time()
    last_beat = -1
    done = {"v": False}

    def _reader():
        try:
            for line in proc.stdout or []:
                line = (line or "").strip()
                if not line:
                    continue
                out_lines.append(line)
                low = line.lower()
                if not callback:
                    continue
                if "writing" in low or "reading" in low:
                    callback(pct_write, line[:70])
                elif "verifying" in low:
                    callback(pct_verify, "검증 중...")
                elif "error" in low or "not in sync" in low:
                    callback(50, line[:70])
        finally:
            done["v"] = True

    th = threading.Thread(target=_reader, daemon=True)
    th.start()
    try:
        while True:
            elapsed = time.time() - t0
            if elapsed > timeout_sec:
                try:
                    proc.kill()
                except Exception:
                    pass
                th.join(timeout=2)
                return False, f"{timeout_sec}초 타임아웃(부트로더 응답없음)", out_lines
            sec = int(elapsed)
            if callback and sec != last_beat and sec >= 1:
                last_beat = sec
                if not any("writing" in x.lower() for x in out_lines):
                    callback(45, f"업로드 중... {sec}s")
            if proc.poll() is not None:
                th.join(timeout=3)
                break
            time.sleep(0.15)
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        ok = proc.returncode == 0
        detail = out_lines[-1] if out_lines else f"code {proc.returncode}"
        return ok, detail, out_lines
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        return False, str(e), out_lines


def _avrdude_cmd(avrdude, conf, hex_path, port):
    return [
        avrdude, "-C", conf,
        "-c", "avr109",
        "-p", "atmega32u4",
        "-P", port,
        "-b", "57600",
        "-D",
        "-U", f"flash:w:{hex_path}:i",
    ]


def flash(callback=None, port=None):
    """아두이노에 펌웨어 업로드. 성공하던 짧은 리셋+1~2회 시도만."""
    if serial is None or list_ports is None:
        return False, "pyserial 없음"

    root = ensure_firmware(callback)
    if not root:
        return False, "펌웨어/avrdude 확보 실패 (GitHub)"

    avrdude = os.path.join(root, "avrdude", "avrdude.exe")
    conf = os.path.join(root, "avrdude", "avrdude.conf")
    hex_path = os.path.join(root, HEX_NAME)
    if not os.path.isfile(avrdude):
        return False, "avrdude.exe 없음"
    if not os.path.isfile(hex_path):
        return False, f"{HEX_NAME} 없음"

    com = find_arduino(preferred=port)
    if not com:
        return False, "아두이노 COM 포트 못찾음 (뚱USB 연결 확인)"

    if callback:
        callback(10, f"아두이노 발견: {com}")

    last_err = ""
    for attempt in (1, 2):
        if callback:
            callback(20, f"부트로더 진입 ({attempt}/2)...")
        old_ports = _ports_set()
        trigger_leonardo_bootloader(com)
        boot_com = pick_upload_port(com, old_ports)
        if callback:
            callback(35, f"업로드 포트: {boot_com}")

        ok, detail, _ = _run_avrdude(
            _avrdude_cmd(avrdude, conf, hex_path, boot_com),
            callback=callback,
            timeout_sec=25,
        )
        if ok:
            if callback:
                callback(100, "업로드 완료!")
            return True, "완료" if attempt == 1 else "완료(재시도)"
        last_err = detail
        if callback:
            callback(30, f"실패 → 재시도 준비 ({detail[:40]})")
        # 다음 시도 전 보드 안정화
        time.sleep(2.0)
        com = find_arduino(preferred=port) or boot_com or com

    return False, f"avrdude 실패: {last_err}"


if __name__ == "__main__":
    print("아두이노 찾는 중...")
    com = find_arduino()
    if not com:
        print("아두이노 없음")
        sys.exit(1)
    print(f"{com} 발견. 업로드 중...")
    ok, msg = flash(lambda p, m: print(f"  {p}% {m}"))
    print(("OK" if ok else "FAIL"), msg)
    sys.exit(0 if ok else 1)
