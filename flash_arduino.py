# -*- coding: utf-8 -*-
"""아두이노 펌웨어 업로드 + 실패 진단 로그.
로그: Desktop/뚱힐러_펌업로그.txt (매번 덮어씀) + 타임스탬프 백업
"""
from __future__ import annotations

import os
import ssl
import sys
import time
import traceback
import tempfile
import threading
import subprocess
import urllib.request
from datetime import datetime

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
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
FLASH_LOG = os.path.join(DESKTOP, "뚱힐러_펌업로그.txt")
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

# 최근 펌업 로그 경로 (UI에서 읽음)
LAST_FLASH_LOG = ""


class FlashLogger:
    def __init__(self):
        self.lines = []
        self.path = FLASH_LOG
        self.started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}"
        self.lines.append(line)
        print(line, flush=True)

    def section(self, title):
        self.log("=" * 60)
        self.log(title)
        self.log("=" * 60)

    def dump_ports(self, tag="PORTS"):
        self.log(f"--- {tag} ---")
        if list_ports is None:
            self.log("pyserial list_ports 없음")
            return
        ports = list(list_ports.comports())
        if not ports:
            self.log("(COM 포트 0개)")
            return
        for p in ports:
            self.log(
                f"  {p.device} | desc={p.description!r} | mfg={p.manufacturer!r} | "
                f"hwid={p.hwid!r}"
            )

    def save(self, ok, summary):
        global LAST_FLASH_LOG
        body = "\n".join(self.lines)
        text = (
            f"뚱힐러 펌업 로그\n"
            f"시작: {self.started}\n"
            f"결과: {'성공' if ok else '실패'} — {summary}\n"
            f"{'=' * 60}\n"
            f"{body}\n"
            f"{'=' * 60}\n"
            f"끝: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        try:
            os.makedirs(DESKTOP, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(text)
            # 실패 시 타임스탬프 백업도 남김
            if not ok:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak = os.path.join(DESKTOP, f"뚱힐러_펌업로그_{stamp}.txt")
                with open(bak, "w", encoding="utf-8") as f:
                    f.write(text)
                self.log(f"백업 로그: {bak}")
                # 백업 경로를 본문에도 다시 기록
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(f"백업: {bak}\n")
            LAST_FLASH_LOG = self.path
        except Exception as e:
            LAST_FLASH_LOG = ""
            self.log(f"로그 파일 저장 실패: {e}")
        return self.path


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def firmware_candidates():
    return [
        os.path.join(HERE, "firmware"),
        os.path.join(DESKTOP, "뚱힐러_github", "firmware"),
        os.path.join(tempfile.gettempdir(), "ddong_firmware"),
    ]


def _has_tools(root):
    return (
        os.path.isfile(os.path.join(root, HEX_NAME))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.exe"))
        and os.path.isfile(os.path.join(root, "avrdude", "avrdude.conf"))
    )


def ensure_firmware(flog=None, callback=None):
    for root in firmware_candidates():
        if _has_tools(root):
            if flog:
                flog.log(f"펌웨어 폴더: {root}")
            return root
    root = os.path.join(tempfile.gettempdir(), "ddong_firmware")
    os.makedirs(os.path.join(root, "avrdude"), exist_ok=True)
    if flog:
        flog.log(f"로컬 없음 → TEMP 다운로드: {root}")
    ctx = _ssl_ctx()
    for remote, local in NEEDED:
        dest = os.path.join(root, local)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            if flog:
                flog.log(f"이미 있음: {dest} ({os.path.getsize(dest)}B)")
            continue
        if callback:
            callback(5, f"다운로드: {os.path.basename(local)}")
        from urllib.parse import quote
        parts = remote.split("/")
        url = GH_RAW + "/" + "/".join(
            quote(p, safe="") if any(ord(c) > 127 for c in p) else p for p in parts
        )
        if flog:
            flog.log(f"다운로드 URL: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ddong"})
            data = urllib.request.urlopen(req, timeout=60, context=ctx).read()
            if len(data) < 1000:
                if flog:
                    flog.log(f"다운로드 너무 작음: {len(data)}B")
                return None
            with open(dest, "wb") as f:
                f.write(data)
            if flog:
                flog.log(f"저장: {dest} ({len(data)}B)")
        except Exception as e:
            if flog:
                flog.log(f"다운로드 실패: {e}")
            return None
    return root if _has_tools(root) else None


def find_arduino_cli(flog=None):
    for c in ARDUINO_CLI_CANDIDATES:
        if os.path.sep in c or (len(c) > 2 and c[1] == ":"):
            exists = os.path.isfile(c)
            if flog:
                flog.log(f"arduino-cli 후보: {c} exists={exists}")
            if exists:
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
            if flog:
                flog.log(f"arduino-cli PATH '{c}' rc={r.returncode} out={(r.stdout or '')[:80]!r}")
            if r.returncode == 0:
                return c
        except Exception as e:
            if flog:
                flog.log(f"arduino-cli PATH '{c}' 실패: {e}")
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


def _kill_stray_avrdude(flog=None):
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/IM", "avrdude.exe"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        if flog:
            flog.log(f"taskkill avrdude rc={r.returncode} out={(r.stdout or r.stderr or '').strip()!r}")
    except Exception as e:
        if flog:
            flog.log(f"taskkill 실패: {e}")


def trigger_leonardo_bootloader(port, flog=None):
    if serial is None or not port:
        if flog:
            flog.log("1200bps 리셋 스킵 (serial/port 없음)")
        return False
    try:
        flog and flog.log(f"1200bps open: {port}")
        s = serial.Serial()
        s.port = port
        s.baudrate = 1200
        s.timeout = 0.1
        try:
            s.setDTR(False)
        except Exception:
            pass
        s.open()
        time.sleep(0.1)
        s.close()
        flog and flog.log("1200bps close OK")
        return True
    except Exception as e:
        flog and flog.log(f"1200bps 리셋 실패: {e!r}")
        try:
            s = serial.Serial(port, 1200, timeout=0.1)
            s.close()
            flog and flog.log("1200bps 간단 open/close OK")
            return True
        except Exception as e2:
            flog and flog.log(f"1200bps 재시도 실패: {e2!r}")
            return False


def wait_for_boot_port(preferred, old_ports, timeout=5.0, callback=None, flog=None):
    t0 = time.time()
    last = -1
    while time.time() - t0 < timeout:
        now = _ports_set()
        sec = int(time.time() - t0)
        if sec != last:
            last = sec
            added = list(now - old_ports)
            gone = list(old_ports - now)
            flog and flog.log(f"부트로더대기 {sec}s now={sorted(now)} added={added} gone={gone}")
            if callback:
                callback(28, f"부트로더 포트 탐색... {sec}s")
        added = [p for p in (now - old_ports) if p]
        if added:
            time.sleep(0.35)
            flog and flog.log(f"새 포트 선택: {added[0]}")
            return added[0]
        time.sleep(0.1)
    if preferred and preferred in _ports_set():
        flog and flog.log(f"타임아웃 → preferred 유지: {preferred}")
        return preferred
    alt = find_arduino(preferred=preferred) or preferred
    flog and flog.log(f"타임아웃 → fallback: {alt}")
    return alt


def _run_cmd(cmd, callback=None, timeout_sec=60, label="upload", flog=None):
    flog and flog.log(f"CMD[{label}]: {' '.join(str(c) for c in cmd)}")
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
        flog and flog.log(f"Popen 실패: {e!r}")
        return False, str(e), []

    out_lines = []
    t0 = time.time()
    last_beat = -1
    done = {"v": False}

    def _reader():
        try:
            for line in proc.stdout or []:
                line = (line or "").rstrip("\r\n")
                if not line.strip():
                    continue
                out_lines.append(line)
                flog and flog.log(f"  [{label}] {line}")
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
                flog and flog.log(f"{label} TIMEOUT {timeout_sec}s — kill")
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
        flog and flog.log(f"{label} 종료 rc={proc.returncode} detail={detail!r} lines={len(out_lines)}")
        return ok, detail, out_lines
    except Exception as e:
        flog and flog.log(f"{label} 예외: {e!r}\n{traceback.format_exc()}")
        try:
            proc.kill()
        except Exception:
            pass
        return False, str(e), out_lines


def flash_via_arduino_cli(hex_path, port, callback=None, flog=None):
    cli = find_arduino_cli(flog=flog)
    if not cli:
        return False, "arduino-cli 없음", []
    if callback:
        callback(30, "arduino-cli 업로드...")
    cmd = [
        cli, "upload",
        "-p", port,
        "--fqbn", FQBN,
        "--input-file", hex_path,
        "-v",
    ]
    return _run_cmd(cmd, callback=callback, timeout_sec=70, label="arduino-cli", flog=flog)


def flash_via_avrdude(root, hex_path, port, callback=None, flog=None):
    avrdude = os.path.join(root, "avrdude", "avrdude.exe")
    conf = os.path.join(root, "avrdude", "avrdude.conf")
    flog and flog.log(f"avrdude={avrdude} exists={os.path.isfile(avrdude)}")
    flog and flog.log(f"conf={conf} exists={os.path.isfile(conf)}")
    if callback:
        callback(25, "1200bps 리셋 후 avrdude...")
    old_ports = _ports_set()
    flog and flog.log(f"리셋 전 ports={sorted(old_ports)}")
    trigger_leonardo_bootloader(port, flog=flog)
    boot = wait_for_boot_port(port, old_ports, timeout=4.0, callback=callback, flog=flog)
    flog and flog.dump_ports("리셋 후")
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
    return _run_cmd(cmd, callback=callback, timeout_sec=30, label="avrdude", flog=flog)


def flash(callback=None, port=None):
    """펌웨어 업로드. return (ok, msg, log_path)."""
    flog = FlashLogger()
    flog.section("뚱힐러 펌업 진단 시작")
    flog.log(f"python={sys.version}")
    flog.log(f"cwd={os.getcwd()}")
    flog.log(f"HERE={HERE}")
    flog.log(f"preferred_port={port!r}")
    flog.dump_ports("시작 시")

    try:
        if serial is None or list_ports is None:
            msg = "pyserial 없음"
            flog.log(msg)
            path = flog.save(False, msg)
            return False, msg, path

        _kill_stray_avrdude(flog=flog)
        time.sleep(0.3)

        root = ensure_firmware(flog=flog, callback=callback)
        if not root:
            msg = "펌웨어/avrdude 확보 실패 (GitHub)"
            path = flog.save(False, msg)
            return False, msg, path

        hex_path = os.path.join(root, HEX_NAME)
        flog.log(f"hex={hex_path} size={os.path.getsize(hex_path) if os.path.isfile(hex_path) else 'MISSING'}")
        if not os.path.isfile(hex_path):
            msg = f"{HEX_NAME} 없음"
            path = flog.save(False, msg)
            return False, msg, path

        com = find_arduino(preferred=port)
        flog.log(f"선택 COM={com!r} (후보={find_arduino_ports()})")
        if not com:
            msg = "아두이노 COM 포트 못찾음 (뚱USB 연결 확인)"
            path = flog.save(False, msg)
            return False, msg, path

        if callback:
            callback(10, f"아두이노 발견: {com}")

        flog.log("시리얼 핸들 해제 대기 1.5s")
        time.sleep(1.5)
        flog.dump_ports("대기 후")

        flog.section("시도1: arduino-cli")
        ok, detail, lines = flash_via_arduino_cli(hex_path, com, callback=callback, flog=flog)
        if ok:
            if callback:
                callback(100, "업로드 완료! (arduino-cli)")
            path = flog.save(True, "완료(arduino-cli)")
            return True, "완료(arduino-cli)", path

        cli_err = detail
        flog.log(f"arduino-cli 실패: {cli_err}")
        if callback:
            callback(22, f"arduino-cli 실패 → avrdude ({str(detail)[:40]})")

        time.sleep(2.0)
        com2 = find_arduino(preferred=port) or com
        flog.log(f"avrdude용 COM={com2!r}")
        _kill_stray_avrdude(flog=flog)

        flog.section("시도2: avrdude")
        ok2, detail2, lines2 = flash_via_avrdude(root, hex_path, com2, callback=callback, flog=flog)
        if ok2:
            if callback:
                callback(100, "업로드 완료! (avrdude)")
            path = flog.save(True, "완료(avrdude)")
            return True, "완료(avrdude)", path

        msg = (
            f"업로드 실패\n"
            f"· arduino-cli: {cli_err}\n"
            f"· avrdude: {detail2}\n"
            f"로그: {FLASH_LOG}"
        )
        flog.log(msg.replace("\n", " | "))
        path = flog.save(False, msg.replace("\n", " / "))
        return False, msg, path
    except Exception as e:
        flog.log(f"flash() 예외: {e!r}\n{traceback.format_exc()}")
        path = flog.save(False, str(e))
        return False, str(e), path


if __name__ == "__main__":
    print("아두이노 찾는 중...")
    com = find_arduino()
    if not com:
        print("아두이노 없음")
        sys.exit(1)
    print(f"{com} 발견. 업로드 중...")
    ok, msg, path = flash(lambda p, m: print(f"  {p}% {m}"))
    print(("OK" if ok else "FAIL"), msg)
    print("LOG", path)
    sys.exit(0 if ok else 1)
