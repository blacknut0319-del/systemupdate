# -*- coding: utf-8 -*-
"""Leonardo 펌업 — Arduino IDE와 같은 1200 자동리셋 + avrdude.

흐름:
  1) GitHub에서 뚱힐러.hex 항상 재다운로드
  2) arduino-cli (IDE와 동일한 1200 리셋)
  3) 시리얼 '!' + 1200 + avrdude
  4) 수동 USB 재연결 폴백
"""
from __future__ import annotations

import os
import ssl
import sys
import time
import zipfile
import traceback
import tempfile
import subprocess
import urllib.request
from datetime import datetime
from urllib.parse import quote

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

HERE = os.path.dirname(os.path.abspath(__file__))
GH_RAW = "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main"
HEX_NAME = "뚱힐러.hex"
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
TMP_ROOT = os.path.join(tempfile.gettempdir(), "ddong_firmware")
CLI_DIR = os.path.join(TMP_ROOT, "arduino-cli")
CLI_ZIP_URL = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
FQBN = "arduino:avr:leonardo"
LEONARDO_BOOT_PID = "0036"
LEONARDO_SKETCH_PID = "8036"
LEONARDO_VID = "2341"
NEEDED_TOOLS = [
    ("firmware/avrdude/avrdude.exe", os.path.join("avrdude", "avrdude.exe")),
    ("firmware/avrdude/avrdude.conf", os.path.join("avrdude", "avrdude.conf")),
    ("firmware/avrdude/libusb0.dll", os.path.join("avrdude", "libusb0.dll")),
]


class FlashLogger:
    """메모리만 기록 (바탕화면 txt 저장 안 함)."""

    def __init__(self):
        self.lines = []

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.lines.append(f"[{ts}] {msg}")

    def section(self, title):
        self.log("=" * 60)
        self.log(title)
        self.log("=" * 60)

    def dump_ports(self, tag="PORTS"):
        self.log(f"--- {tag} ---")
        if list_ports is None:
            self.log("list_ports 없음")
            return
        ports = list(list_ports.comports())
        if not ports:
            self.log("(COM 0개)")
            return
        for p in ports:
            self.log(
                f"  {p.device} [{_port_mode(p)}] desc={p.description!r} hwid={p.hwid!r}"
            )

    def save(self, ok, summary):
        return ""

def _port_mode(p):
    hu = (p.hwid or "").upper()
    if LEONARDO_VID in hu and LEONARDO_BOOT_PID in hu:
        return "BOOTLOADER"
    if LEONARDO_VID in hu and LEONARDO_SKETCH_PID in hu:
        return "SKETCH"
    return "OTHER"


def _is_bootloader_port(p):
    return _port_mode(p) == "BOOTLOADER"


def _is_leonardo_any(p):
    return LEONARDO_VID in (p.hwid or "").upper()


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _gh_url(remote):
    parts = remote.split("/")
    return GH_RAW + "/" + "/".join(
        quote(p, safe="") if any(ord(c) > 127 for c in p) else p for p in parts
    )


def _download(remote, dest, flog=None, callback=None, label=None):
    if callback:
        callback(5, f"다운로드: {label or os.path.basename(dest)}")
    url = _gh_url(remote)
    flog and flog.log(f"GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "ddong", "Cache-Control": "no-cache"})
    data = urllib.request.urlopen(req, timeout=60, context=_ssl_ctx()).read()
    if len(data) < 1000:
        raise RuntimeError(f"너무 작음: {len(data)}")
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    flog and flog.log(f"저장 {dest} size={len(data)}")
    return len(data)


def ensure_firmware(flog=None, callback=None):
    """hex: 로컬(개발폴더) 우선 → 없으면 GitHub. avrdude는 캐시 OK."""
    root = TMP_ROOT
    os.makedirs(os.path.join(root, "avrdude"), exist_ok=True)
    hex_dest = os.path.join(root, HEX_NAME)

    # 로컬 hex 우선 (개발/테스트 — GitHub 옛 hex보다 먼저)
    for cand in (
        os.path.join(HERE, "firmware", HEX_NAME),
        os.path.join(DESKTOP, "뚱힐러_github", "firmware", HEX_NAME),
    ):
        if os.path.isfile(cand) and os.path.getsize(cand) > 1000:
            try:
                import shutil
                shutil.copy2(cand, hex_dest)
                flog and flog.log(f"hex 로컬: {cand} size={os.path.getsize(hex_dest)}")
                break
            except Exception as e:
                flog and flog.log(f"hex 로컬복사 실패: {e}")

    # 로컬 avrdude 복사
    for cand in (
        os.path.join(HERE, "firmware"),
        os.path.join(DESKTOP, "뚱힐러_github", "firmware"),
    ):
        if os.path.isfile(os.path.join(cand, "avrdude", "avrdude.exe")):
            for name in ("avrdude.exe", "avrdude.conf", "libusb0.dll"):
                src = os.path.join(cand, "avrdude", name)
                dst = os.path.join(root, "avrdude", name)
                if os.path.isfile(src) and (
                    not os.path.isfile(dst) or os.path.getsize(dst) < 1000
                ):
                    try:
                        import shutil
                        shutil.copy2(src, dst)
                    except Exception:
                        pass
            break

    for remote, local in NEEDED_TOOLS:
        dest = os.path.join(root, local)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            continue
        try:
            _download(remote, dest, flog=flog, callback=callback)
        except Exception as e:
            flog and flog.log(f"도구 다운로드 실패: {e}")
            return None

    # hex 없으면 GitHub
    if not os.path.isfile(hex_dest) or os.path.getsize(hex_dest) < 1000:
        old = os.path.getsize(hex_dest) if os.path.isfile(hex_dest) else 0
        try:
            new_sz = _download(
                f"firmware/{HEX_NAME}", hex_dest, flog=flog, callback=callback, label=HEX_NAME
            )
            flog and flog.log(f"hex GitHub: {old} → {new_sz}")
        except Exception as e:
            flog and flog.log(f"hex 다운로드 실패: {e}")
            if not os.path.isfile(hex_dest) or os.path.getsize(hex_dest) < 1000:
                return None

    flog and flog.log(f"펌웨어 폴더: {root}")
    return root


def find_arduino(preferred=None):
    if list_ports is None:
        return None
    ports_now = {p.device for p in list_ports.comports()}
    if preferred and preferred in ports_now:
        return preferred
    for p in list_ports.comports():
        if _is_leonardo_any(p) or _is_bootloader_port(p):
            return p.device
    for p in list_ports.comports():
        d = f"{p.description or ''} {p.manufacturer or ''}".upper()
        if any(k in d for k in ("CH340", "ARDUINO", "LEONARDO", "USB", "SERIAL", "CP210")) or "직렬" in (p.description or ""):
            return p.device
    return None


def find_bootloader_port():
    if list_ports is None:
        return None
    for p in list_ports.comports():
        if _is_bootloader_port(p):
            return p.device
    return None


def _kill_stray_avrdude(flog=None):
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "avrdude.exe"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception:
        pass


def wait_bootloader(timeout=8.0, callback=None, flog=None, hint="부트로더 대기"):
    t0 = time.time()
    last = -1
    while time.time() - t0 < timeout:
        sec = int(time.time() - t0)
        boot = find_bootloader_port()
        if sec != last:
            last = sec
            flog and flog.dump_ports(f"{hint} {sec}s boot={boot}")
            if callback:
                callback(30, f"{hint} {sec}s")
        if boot:
            time.sleep(0.35)
            return boot
        time.sleep(0.12)
    return None


def _enter_bootloader_serial_cmd(port, flog=None):
    s = serial.Serial()
    s.port = port
    s.baudrate = 9600
    s.timeout = 0.2
    s.write_timeout = 1.0
    s.dsrdtr = False
    s.rtscts = False
    s.open()
    try:
        try:
            s.reset_input_buffer()
        except Exception:
            pass
        time.sleep(0.2)
        # 여러 번 — 한 바이트 유실 대비
        for _ in range(3):
            s.write(b"!")
            try:
                s.flush()
            except Exception:
                pass
            time.sleep(0.05)
    finally:
        try:
            s.close()
        except Exception:
            pass
    flog and flog.log("touch: serial '!' OK")


def _probe_firmware(port, flog=None):
    """펌업 전 'V' 조회 — DDONG-V4 / DDONG-WDT4 등."""
    s = None
    try:
        s = serial.Serial(port, 9600, timeout=0.2, write_timeout=1.0)
        try:
            s.reset_input_buffer()
        except Exception:
            pass
        time.sleep(0.12)
        s.write(b"V")
        try:
            s.flush()
        except Exception:
            pass
        buf = b""
        t0 = time.time()
        while time.time() - t0 < 1.6:
            n = getattr(s, "in_waiting", 0) or 0
            if n:
                buf += s.read(n)
                if b"DDONG" in buf or b"\n" in buf:
                    break
            time.sleep(0.05)
        ver = buf.decode("ascii", errors="ignore").strip()
        flog and flog.log(f"probe V: {ver!r}")
        return ver
    except Exception as e:
        flog and flog.log(f"probe V 실패: {e!r}")
        return ""
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


def _has_ddong_fw(ver):
    v = (ver or "").upper().replace(" ", "")
    return "DDONG" in v


def _touch_dtr_reset(port, flog=None):
    """Leonardo CDC 소프트리셋 (DTR 토글). 리셋 버튼 없는 보드용."""
    s = None
    try:
        s = serial.Serial()
        s.port = port
        s.baudrate = 9600
        s.dsrdtr = True
        s.rtscts = False
        s.open()
        try:
            s.setDTR(False)
            s.setRTS(False)
            time.sleep(0.05)
            s.setDTR(True)
            time.sleep(0.05)
            s.setDTR(False)
        except Exception:
            pass
        time.sleep(0.12)
        s.baudrate = 1200
        time.sleep(0.12)
        flog and flog.log("touch: DTR+1200 OK")
    except Exception as e:
        flog and flog.log(f"DTR+1200: {e!r}")
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


def _touch_1200_simple(port, flog=None):
    """처음 성공하던 짧은 1200 open/close."""
    try:
        s = serial.Serial(port, 1200)
        try:
            s.dtr = False
        except Exception:
            pass
        time.sleep(0.1)
        s.close()
    except Exception:
        s = serial.Serial()
        s.port = port
        s.baudrate = 1200
        s.dtr = False
        s.open()
        time.sleep(0.1)
        s.close()
    flog and flog.log("touch: simple 1200 OK")


def _enter_bootloader(port, flog=None, rounds=4):
    """! 명령 + DTR + 1200 조합으로 부트로더 진입 시도."""
    boot = find_bootloader_port()
    if boot:
        return boot
    for i in range(rounds):
        try:
            _enter_bootloader_serial_cmd(port, flog=flog)
        except Exception as e:
            flog and flog.log(f"'!' r{i}: {e!r}")
        boot = wait_bootloader(timeout=2.5, flog=flog, hint=f"!{i}")
        if boot:
            return boot
        try:
            _touch_dtr_reset(port, flog=flog)
        except Exception:
            pass
        try:
            _touch_1200_simple(port, flog=flog)
        except Exception as e:
            flog and flog.log(f"1200 r{i}: {e!r}")
        time.sleep(0.45)
        boot = find_bootloader_port()
        if boot:
            return boot
    return None


def _run_avrdude(root, hex_path, boot_port, callback=None, flog=None):
    avrdude = os.path.join(root, "avrdude", "avrdude.exe")
    conf = os.path.join(root, "avrdude", "avrdude.conf")
    cmd = [
        avrdude, "-C", conf,
        "-c", "avr109", "-p", "atmega32u4",
        "-P", boot_port, "-b", "57600", "-D",
        "-U", f"flash:w:{hex_path}:i",
    ]
    flog and flog.log("CMD: " + " ".join(cmd))
    if callback:
        callback(55, f"avrdude ({boot_port})")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    )
    lines = []
    t0 = time.time()
    while True:
        if time.time() - t0 > 30:
            try:
                proc.kill()
            except Exception:
                pass
            return False, "avrdude 30초 타임아웃"
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            line = line.rstrip()
            lines.append(line)
            flog and flog.log(f"  [avrdude] {line}")
            if callback and "writing" in line.lower():
                callback(75, line[:70])
        elif proc.poll() is not None:
            break
        else:
            time.sleep(0.05)
    return proc.returncode == 0, (lines[-1] if lines else f"code {proc.returncode}")


def ensure_arduino_cli(flog=None, callback=None):
    exe = os.path.join(CLI_DIR, "arduino-cli.exe")
    if os.path.isfile(exe):
        return exe
    os.makedirs(CLI_DIR, exist_ok=True)
    zip_path = os.path.join(TMP_ROOT, "arduino-cli.zip")
    if callback:
        callback(12, "arduino-cli 다운로드...")
    try:
        req = urllib.request.Request(CLI_ZIP_URL, headers={"User-Agent": "ddong"})
        with urllib.request.urlopen(req, timeout=180, context=_ssl_ctx()) as r:
            data = r.read()
        with open(zip_path, "wb") as f:
            f.write(data)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(CLI_DIR)
        if not os.path.isfile(exe):
            for root, _, files in os.walk(CLI_DIR):
                if "arduino-cli.exe" in files:
                    import shutil
                    shutil.copy2(os.path.join(root, "arduino-cli.exe"), exe)
                    break
        return exe if os.path.isfile(exe) else None
    except Exception as e:
        flog and flog.log(f"arduino-cli 설치 실패: {e!r}")
        return None


def flash_via_arduino_cli(hex_path, port, flog=None, callback=None):
    cli = ensure_arduino_cli(flog=flog, callback=callback)
    if not cli:
        return False, "arduino-cli 없음"
    try:
        subprocess.run(
            [cli, "core", "install", "arduino:avr"],
            capture_output=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception:
        pass
    cmd = [cli, "upload", "-p", port, "--fqbn", FQBN, "--input-file", hex_path, "-v"]
    flog and flog.log("CMD: " + " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except Exception as e:
        return False, str(e)
    lines = []
    t0 = time.time()
    while True:
        if time.time() - t0 > 90:
            try:
                proc.kill()
            except Exception:
                pass
            return False, "cli 타임아웃"
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            line = line.rstrip()
            lines.append(line)
            flog and flog.log(f"  [cli] {line}")
        elif proc.poll() is not None:
            break
        else:
            time.sleep(0.05)
    return proc.returncode == 0, (lines[-1] if lines else f"code {proc.returncode}")


def _flash_once_1200_avrdude(root, hex_path, port, callback=None, flog=None):
    """IDE와 같이 1200 한 번 → 부트로더 대기 → avrdude 1회."""
    if callback:
        callback(40, "1200 리셋 (IDE 방식)")
    try:
        _touch_1200_simple(port, flog=flog)
    except Exception as e:
        flog and flog.log(f"1200 실패: {e!r}")
        return False, "1200 리셋 실패"
    time.sleep(0.35)
    boot = wait_bootloader(timeout=6.0, callback=callback, flog=flog, hint="1200")
    if not boot:
        boot = port
        flog and flog.log(f"부트로더 COM 미검출 → sketch 포트 {port} 로 시도")
    ok, detail = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
    return ok, detail


def _flash_once_bang_avrdude(root, hex_path, port, callback=None, flog=None):
    """옛 시스템 WDT(1/2) 등 — 1200 대신 펌웨어 '!' 로 부트로더 진입."""
    if callback:
        callback(45, "! 부트로더 (옛 WDT용)")
    try:
        _enter_bootloader_serial_cmd(port, flog=flog)
    except Exception as e:
        flog and flog.log(f"'!' 실패: {e!r}")
        return False, "! 명령 실패"
    time.sleep(0.4)
    boot = wait_bootloader(timeout=5.0, callback=callback, flog=flog, hint="!")
    if not boot:
        boot = find_bootloader_port() or port
        flog and flog.log(f"! 후 boot={boot}")
    ok, detail = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
    return ok, detail


def flash(callback=None, port=None, ask_manual_reset=None):
    """return (ok, msg, log_path). Arduino IDE와 동일: cli 먼저, COM 최소 사용."""
    flog = FlashLogger()
    flog.section("펌업 시작 (IDE 방식: cli → 1200 → !)")
    flog.log(f"python={sys.version}")
    flog.log(f"preferred={port!r}")
    flog.dump_ports("시작")

    try:
        if serial is None:
            msg = "pyserial 없음"
            return False, msg, flog.save(False, msg)

        _kill_stray_avrdude(flog)
        time.sleep(0.3)

        root = ensure_firmware(flog=flog, callback=callback)
        if not root:
            msg = "펌웨어 확보 실패"
            return False, msg, flog.save(False, msg)
        hex_path = os.path.join(root, HEX_NAME)
        hex_sz = os.path.getsize(hex_path)
        flog.log(f"hex={hex_path} size={hex_sz}")

        com = find_arduino(preferred=port)
        if not com:
            msg = "아두이노 COM 없음"
            return False, msg, flog.save(False, msg)
        if callback:
            callback(10, f"장치: {com}")

        # ── 1) arduino-cli (Arduino IDE와 동일) ──
        flog.section("1) arduino-cli (IDE 방식)")
        if callback:
            callback(20, "arduino-cli 업로드…")
        ok_cli, detail_cli = flash_via_arduino_cli(hex_path, com, flog=flog, callback=callback)
        if ok_cli:
            if callback:
                callback(100, "업로드 완료!")
            return True, "완료(cli)", flog.save(True, "완료(cli)")
        flog.log(f"cli 실패: {detail_cli}")

        # ── 2) 1200 + avrdude 1회 ──
        flog.section("2) 1200 + avrdude")
        com = find_arduino(preferred=port) or com
        ok_avr, detail_avr = _flash_once_1200_avrdude(
            root, hex_path, com, callback=callback, flog=flog
        )
        if ok_avr:
            if callback:
                callback(100, "업로드 완료!")
            return True, f"완료(avrdude/{com})", flog.save(True, f"완료(avrdude/{com})")
        flog.log(f"avrdude 실패: {detail_avr}")

        # ── 3) '!' 부트로더 (옛 WDT1/2 — 1200 자동리셋 안 먹는 보드) ──
        flog.section("3) ! 부트로더 (옛 WDT)")
        com = find_arduino(preferred=port) or com
        ok_bang, detail_bang = _flash_once_bang_avrdude(
            root, hex_path, com, callback=callback, flog=flog
        )
        if ok_bang:
            if callback:
                callback(100, "업로드 완료!")
            return True, f"완료(!/{com})", flog.save(True, f"완료(!/{com})")
        flog.log(f"! avrdude 실패: {detail_bang}")

        # ── 4) 수동 USB 재연결 후 1회 더 ──
        if callable(ask_manual_reset):
            flog.section("4) USB 재연결 후 재시도")
            if callback:
                callback(25, "USB 재연결 안내")
            try:
                go = bool(ask_manual_reset())
            except Exception:
                go = False
            if go:
                time.sleep(0.5)
                com = find_arduino(preferred=port) or find_arduino()
                if com:
                    ok_cli2, _ = flash_via_arduino_cli(hex_path, com, flog=flog, callback=callback)
                    if ok_cli2:
                        if callback:
                            callback(100, "업로드 완료!")
                        return True, "완료(cli/수동)", flog.save(True, "완료(cli/수동)")
                    ok_avr2, detail_avr2 = _flash_once_1200_avrdude(
                        root, hex_path, com, callback=callback, flog=flog
                    )
                    if ok_avr2:
                        if callback:
                            callback(100, "업로드 완료!")
                        return True, "완료(avrdude/수동)", flog.save(True, "완료(avrdude/수동)")
                    ok_bang2, detail_bang2 = _flash_once_bang_avrdude(
                        root, hex_path, com, callback=callback, flog=flog
                    )
                    if ok_bang2:
                        if callback:
                            callback(100, "업로드 완료!")
                        return True, "완료(!/수동)", flog.save(True, "완료(!/수동)")
                    flog.log(f"수동 avrdude 실패: {detail_avr2} / ! {detail_bang2}")

        msg = (
            "자동 펌업 실패.\n"
            "· 옛 워치독(WDT1/2) 펌이면 USB 뽑았다 꽂고 【펌업】 한 번 더.\n"
            "· 그래도 안 되면 Arduino IDE로 이번 1회만 수동 업로드.\n"
            f"· cli: {detail_cli}\n"
            f"· 1200: {detail_avr}\n"
            f"· !: {detail_bang}"
        )
        return False, msg, flog.save(False, msg.replace("\n", " / "))
    except Exception as e:
        flog.log(traceback.format_exc())
        return False, str(e), flog.save(False, str(e))


if __name__ == "__main__":
    ok, msg, path = flash(lambda p, m: print(f"{p}% {m}"))
    print(("OK" if ok else "FAIL"), msg)
    print("LOG", path)
    sys.exit(0 if ok else 1)
