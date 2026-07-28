# -*- coding: utf-8 -*-
"""아두이노 펌웨어 업로드 — Leonardo(ATmega32u4) + 번들 avrdude.
COM 자동감지, 1200bps 부트로더 진입, GitHub에서 hex/avrdude 자동확보."""
from __future__ import annotations

import os
import ssl
import sys
import time
import tempfile
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
    cands = [
        os.path.join(HERE, "firmware"),
        os.path.join(os.path.expanduser("~"), "Desktop", "뚱힐러_github", "firmware"),
        os.path.join(tempfile.gettempdir(), "ddong_firmware"),
    ]
    return cands


def _has_tools(root):
    return (
        os.path.isfile(os.path.join(root, HEX_NAME))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.exe"))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.conf"))
    )


def ensure_firmware(callback=None):
    """로컬 firmware 폴더 확보. 없으면 GitHub에서 TEMP로 받음."""
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
        url = f"{GH_RAW}/{urllib.request.quote(remote)}"
        # quote breaks path slashes — build manually
        url = f"{GH_RAW}/{remote}"
        try:
            # 한글 파일명 인코딩
            from urllib.parse import quote
            parts = remote.split("/")
            url = GH_RAW + "/" + "/".join(quote(p, safe="") if any(ord(c) > 127 for c in p) else p for p in parts)
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
    """아두이노로 보이는 COM 포트 목록.
    뚱힐러 auto_find_arduino()와 같은 판정(USB/직렬/VID)을 써서
    '연결은 되는데 펌업만 포트 못 찾음'이 안 나오게 함."""
    if list_ports is None:
        return []
    ports = list(list_ports.comports())
    found = []

    def _add(dev):
        if dev and dev not in found:
            found.append(dev)

    # 1) 우선순위: 알려진 VID (Logitech→Arduino 등 기존 로직과 동일)
    for p in ports:
        h = (p.hwid or "").upper()
        if "046D" in h and "C08B" in h:
            _add(p.device)
    for p in ports:
        h = (p.hwid or "").upper()
        if "2341" in h or "2A03" in h or "1B4F" in h:  # Arduino / official / SparkFun
            _add(p.device)
    # 2) 설명/제조사 — 연결에 쓰는 것과 동일하게 USB·직렬 포함
    for p in ports:
        d = f"{p.description or ''} {p.manufacturer or ''}"
        du = d.upper()
        dl = d.lower()
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
    """preferred(이미 연결된 COM)가 살아있으면 그걸 최우선."""
    ports_now = {p.device for p in list_ports.comports()} if list_ports else set()
    if preferred and preferred in ports_now:
        return preferred
    ports = find_arduino_ports()
    if preferred and preferred in ports:
        return preferred
    return ports[0] if ports else None


def _ports_set():
    if list_ports is None:
        return set()
    return {p.device for p in list_ports.comports()}


def trigger_leonardo_bootloader(port):
    """Leonardo: 1200bps로 열었다 닫으면 부트로더 진입."""
    if serial is None:
        return
    try:
        s = serial.Serial(port, 1200)
        s.dtr = False
        s.close()
    except Exception:
        try:
            s = serial.Serial()
            s.port = port
            s.baudrate = 1200
            s.dtr = False
            s.open()
            s.close()
        except Exception:
            pass
    time.sleep(0.5)


def wait_bootloader_port(old_port, old_ports, timeout=12.0, callback=None):
    """부트로더 진입 후 COM 대기.

    중요: 리셋 직후에도 old_port가 잠깐 남아있을 수 있음.
    그 상태에서 바로 리턴하면 앱 포트에 avrdude가 붙어서 35%에서 영원히 대기함.
    → 포트가 한번 사라졌다가 다시 뜨거나, 새 COM이 생길 때까지 기다림.
    """
    t0 = time.time()
    saw_disconnect = old_port not in _ports_set()
    last_report = -1
    while time.time() - t0 < timeout:
        now = _ports_set()
        elapsed = int(time.time() - t0)
        if callback and elapsed != last_report:
            last_report = elapsed
            callback(28, f"부트로더 대기 중... {elapsed}s")

        if old_port not in now:
            saw_disconnect = True

        added = [p for p in (now - old_ports) if p]
        if added:
            time.sleep(0.4)  # 부트로더 준비
            return added[0]

        # 같은 COM으로 다시 열거된 경우 — 반드시 한번 끊긴 뒤에만 인정
        if saw_disconnect and old_port in now:
            time.sleep(0.5)
            return old_port

        time.sleep(0.12)

    # 타임아웃: 현재 잡히는 포트라도 반환 (재시도용)
    if callback:
        callback(30, "부트로더 대기 시간초과 — 현재 포트로 시도")
    return find_arduino(preferred=old_port) or old_port


def _run_avrdude(cmd, callback=None, timeout_sec=45, pct_write=55, pct_verify=80):
    """avrdude 실행. 출력 없으면 멈춘 것처럼 보이므로 진행로그+강제 타임아웃."""
    import threading
    if callback:
        callback(max(36, pct_write - 15), "avrdude 실행 중...")
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
                if callback:
                    if "writing" in low or "reading" in low:
                        callback(pct_write, line[:70])
                    elif "verifying" in low:
                        callback(pct_verify, "검증 중...")
                    elif "error" in low or "not in sync" in low or "can't open" in low:
                        callback(pct_write, line[:70])
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
                return False, f"avrdude 응답없음({timeout_sec}초 타임아웃) — USB뽑았다가 다시 꽂고 재시도", out_lines
            sec = int(elapsed)
            if callback and sec != last_beat and sec >= 1:
                last_beat = sec
                if not any("writing" in x.lower() for x in out_lines):
                    callback(max(36, pct_write - 10), f"업로드 대기 중... {sec}s / {timeout_sec}s")
            if proc.poll() is not None:
                th.join(timeout=3)
                break
            time.sleep(0.2)
        try:
            proc.wait(timeout=5)
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


def flash(callback=None, port=None):
    """아두이노에 펌웨어 업로드. callback(pct, msg). return (ok, msg)."""
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

    old_ports = _ports_set()
    if callback:
        callback(20, "부트로더 진입 중(1200bps 리셋)...")
    trigger_leonardo_bootloader(com)
    boot_com = wait_bootloader_port(com, old_ports, callback=callback)
    if callback:
        callback(35, f"업로드 포트: {boot_com}")

    # Leonardo / Micro: avr109 + atmega32u4 (-v 로 진행출력이 안 막히게)
    cmd = [
        avrdude, "-C", conf, "-v",
        "-c", "avr109",
        "-p", "atmega32u4",
        "-P", boot_com,
        "-b", "57600",
        "-D",
        "-U", f"flash:w:{hex_path}:i",
    ]

    ok1, detail1, lines1 = _run_avrdude(cmd, callback=callback, timeout_sec=45)
    if ok1:
        if callback:
            callback(100, "업로드 완료!")
        return True, "완료"

    # 한 번 더: 포트 재탐색 후 Leonardo 재시도
    if callback:
        callback(38, "재시도: 부트로더 다시 진입...")
    time.sleep(1.5)
    com_retry = find_arduino(preferred=port) or com
    old_ports = _ports_set()
    trigger_leonardo_bootloader(com_retry)
    boot_com2 = wait_bootloader_port(com_retry, old_ports, callback=callback)
    cmd[cmd.index("-P") + 1] = boot_com2
    ok1b, detail1b, lines1b = _run_avrdude(cmd, callback=callback, timeout_sec=45)
    if ok1b:
        if callback:
            callback(100, "업로드 완료!")
        return True, "완료(재시도)"

    # 구형/호환보드 폴백: Uno 프로토콜 (일부 CH340 클론)
    if callback:
        callback(40, "Leonardo 실패 → 호환모드 재시도...")
    time.sleep(1.0)
    com2 = find_arduino(preferred=port) or com
    cmd2 = [
        avrdude, "-C", conf, "-v",
        "-c", "arduino",
        "-p", "atmega328p",
        "-P", com2,
        "-b", "115200",
        "-U", f"flash:w:{hex_path}:i",
    ]
    ok2, detail2, lines2 = _run_avrdude(cmd2, callback=callback, timeout_sec=40, pct_write=70, pct_verify=90)
    if ok2:
        if callback:
            callback(100, "업로드 완료!(호환)")
        return True, "완료(호환모드)"

    detail = detail1b or detail1 or detail2 or "알 수 없음"
    return False, f"avrdude 실패: {detail}"


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
