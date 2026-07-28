# -*- coding: utf-8 -*-
"""아두이노 펌웨어 업로드.
1순위: Arduino IDE의 arduino-cli (Leonardo 리셋/포트전환을 IDE와 동일하게 처리)
2순위: 번들 avrdude + 1200bps 터치
"""
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
FQBN = "arduino:avr:leonardo"
NEEDED = [
    ("firmware/뚱힐러.hex", HEX_NAME),
    ("firmware/avrdude/avrdude.exe", os.path.join("avrdude", "avrdude.exe")),
    ("firmware/avrdude/avrdude.conf", os.path.join("avrdude", "avrdude.conf")),
    ("firmware/avrdude/libusb0.dll", os.path.join("avrdude", "libusb0.dll")),
]

ARDUINO_CLI_CANDIDATES = [
    r"C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe",
    r"C:\Program Files (x86)\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe",
    "arduino-cli",
    "arduino-cli.exe",
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


def find_arduino_cli():
    for c in ARDUINO_CLI_CANDIDATES:
        if os.path.sep in c or (len(c) > 2 and c[1] == ":"):
            if os.path.isfile(c):
                return c
            continue
        try:
            r = subprocess.run(
                [c, "version"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            )
            if r.returncode == 0:
                return c
        except Exception:
            continue
    return None


def find_arduino_ports():
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


def _kill_stray_avrdude():
    """이전 펌업이 남긴 avrdude가 COM을 붙잡고 있으면 부트로더 진입이 실패함."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "avrdude.exe"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception:
        pass


def trigger_leonardo_bootloader(port):
    """1200bps touch — 포트가 비어 있어야 함(다른 프로그램이 열면 실패)."""
    if serial is None or not port:
        return
    try:
        s = serial.Serial()
        s.port = port
        s.baudrate = 1200
        s.timeout = 0.1
        s.setDTR(False)
        s.open()
        time.sleep(0.1)
        s.close()
    except Exception:
        try:
            s = serial.Serial(port, 1200, timeout=0.1)
            s.close()
        except Exception:
            pass


def wait_for_boot_port(preferred, old_ports, timeout=5.0, callback=None):
    """새 COM 우선, 없으면 preferred. 부트로더 창이 끝나기 전(짧게)만 대기."""
    t0 = time.time()
    last = -1
    while time.time() - t0 < timeout:
        now = _ports_set()
        sec = int(time.time() - t0)
        if callback and sec != last:
            last = sec
            callback(28, f"부트로더 포트 탐색... {sec}s")
        added = [p for p in (now - old_ports) if p]
        if added:
            time.sleep(0.35)
            return added[0]
        time.sleep(0.1)
    if preferred and preferred in _ports_set():
        return preferred
    return find_arduino(preferred=preferred) or preferred


def _run_cmd(cmd, callback=None, timeout_sec=60, label="upload"):
    if callback:
        callback(40, f"{label} 실행...")
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
                if "writing" in low or "upload" in low or "플래시" in line:
                    callback(60, line[:70])
                elif "verifying" in low or "검증" in line:
                    callback(85, "검증 중...")
                elif "error" in low or "not in sync" in low or "can't open" in low:
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
                return False, f"{timeout_sec}초 타임아웃", out_lines
            sec = int(elapsed)
            if callback and sec != last_beat and sec >= 1:
                last_beat = sec
                if not any(("writing" in x.lower()) or ("upload" in x.lower()) for x in out_lines):
                    callback(45, f"{label} 대기... {sec}s")
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


def flash_via_arduino_cli(hex_path, port, callback=None):
    cli = find_arduino_cli()
    if not cli:
        return False, "arduino-cli 없음", []
    if callback:
        callback(30, "arduino-cli 업로드 (IDE와 동일 방식)...")
    # -i / --input-file : 미리 컴파일된 hex
    cmd = [
        cli, "upload",
        "-p", port,
        "--fqbn", FQBN,
        "--input-file", hex_path,
        "-v",
    ]
    return _run_cmd(cmd, callback=callback, timeout_sec=70, label="arduino-cli")


def flash_via_avrdude(root, hex_path, port, callback=None):
    avrdude = os.path.join(root, "avrdude", "avrdude.exe")
    conf = os.path.join(root, "avrdude", "avrdude.conf")
    if callback:
        callback(25, "1200bps 리셋 후 avrdude...")
    old_ports = _ports_set()
    trigger_leonardo_bootloader(port)
    boot = wait_for_boot_port(port, old_ports, timeout=4.0, callback=callback)
    if callback:
        callback(35, f"avrdude 포트: {boot}")
    cmd = [
        avrdude, "-C", conf,
        "-c", "avr109",
        "-p", "atmega32u4",
        "-P", boot,
        "-b", "57600",
        "-D",
        "-U", f"flash:w:{hex_path}:i",
    ]
    return _run_cmd(cmd, callback=callback, timeout_sec=30, label="avrdude")


def flash(callback=None, port=None):
    """펌웨어 업로드. return (ok, msg)."""
    if serial is None or list_ports is None:
        return False, "pyserial 없음"

    _kill_stray_avrdude()
    time.sleep(0.3)

    root = ensure_firmware(callback)
    if not root:
        return False, "펌웨어/avrdude 확보 실패 (GitHub)"

    hex_path = os.path.join(root, HEX_NAME)
    if not os.path.isfile(hex_path):
        return False, f"{HEX_NAME} 없음"

    com = find_arduino(preferred=port)
    if not com:
        return False, "아두이노 COM 포트 못찾음 (뚱USB 연결 확인)"

    if callback:
        callback(10, f"아두이노 발견: {com}")

    # Windows에서 시리얼 핸들이 완전히 풀릴 시간
    time.sleep(1.5)

    # 1) arduino-cli (가장 안정)
    ok, detail, lines = flash_via_arduino_cli(hex_path, com, callback=callback)
    if ok:
        if callback:
            callback(100, "업로드 완료! (arduino-cli)")
        return True, "완료(arduino-cli)"

    cli_err = detail
    if callback:
        callback(22, f"arduino-cli 실패 → avrdude 재시도 ({str(detail)[:40]})")

    # 포트 다시 찾고, 한 번 더 여유
    time.sleep(2.0)
    com2 = find_arduino(preferred=port) or com
    _kill_stray_avrdude()
    ok2, detail2, _ = flash_via_avrdude(root, hex_path, com2, callback=callback)
    if ok2:
        if callback:
            callback(100, "업로드 완료! (avrdude)")
        return True, "완료(avrdude)"

    return False, (
        f"업로드 실패\n"
        f"· arduino-cli: {cli_err}\n"
        f"· avrdude: {detail2}\n"
        f"USB 뽑았다가 꽂고, 뚱힐러를 끈 뒤 다시 [펌업] 하세요."
    )


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
