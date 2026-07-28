# -*- coding: utf-8 -*-
"""Leonardo 펌업 — 리셋버튼 없이 자동 진입.

원인(로그로 확정):
  - WDT 켠 스케치는 Leonardo 1200bps soft-reset가 깨짐 (PID 8036→0036 안 됨)
  - arduino-cli도 동일: Performing 1200-bps touch → No upload port → butterfly_recv fail
  - 수동 더블리셋은 부트로더 진입 OK

해결:
  1) 우선 시리얼 '!' 명령 → 펌웨어가 Caterina 매직키+WDT로 부트로더 점프 (리셋버튼 불필요)
  2) 옛 WDT 펌(명령 없음)이면 1200/cli 재시도 후, 버튼 있는 보드만 1회 수동
  3) 새 펌(DDONG-WDT2) 올린 뒤부터는 '!' 만으로 자동 펌업
"""
from __future__ import annotations

import os
import re
import ssl
import sys
import time
import zipfile
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
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
FLASH_LOG = os.path.join(DESKTOP, "뚱힐러_펌업로그.txt")
TMP_ROOT = os.path.join(tempfile.gettempdir(), "ddong_firmware")
CLI_DIR = os.path.join(TMP_ROOT, "arduino-cli")
CLI_ZIP_URL = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
FQBN = "arduino:avr:leonardo"
LEONARDO_BOOT_PID = "0036"
LEONARDO_SKETCH_PID = "8036"
LEONARDO_VID = "2341"
NEEDED = [
    ("firmware/뚱힐러.hex", HEX_NAME),
    ("firmware/avrdude/avrdude.exe", os.path.join("avrdude", "avrdude.exe")),
    ("firmware/avrdude/avrdude.conf", os.path.join("avrdude", "avrdude.conf")),
    ("firmware/avrdude/libusb0.dll", os.path.join("avrdude", "libusb0.dll")),
]
LAST_FLASH_LOG = ""


class FlashLogger:
    def __init__(self):
        self.lines = []
        self.path = FLASH_LOG
        self.started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        global LAST_FLASH_LOG
        body = "\n".join(self.lines)
        text = (
            f"뚱힐러 펌업 로그\n시작: {self.started}\n"
            f"결과: {'성공' if ok else '실패'} — {summary}\n"
            f"{'=' * 60}\n{body}\n{'=' * 60}\n"
            f"끝: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        try:
            os.makedirs(DESKTOP, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(text)
            if not ok:
                bak = os.path.join(
                    DESKTOP, f"뚱힐러_펌업로그_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                )
                with open(bak, "w", encoding="utf-8") as f:
                    f.write(text)
            LAST_FLASH_LOG = self.path
        except Exception:
            LAST_FLASH_LOG = ""
        return self.path


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


def firmware_candidates():
    return [
        os.path.join(HERE, "firmware"),
        os.path.join(DESKTOP, "뚱힐러_github", "firmware"),
        TMP_ROOT,
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
            flog and flog.log(f"펌웨어 폴더: {root}")
            return root
    root = TMP_ROOT
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
        except Exception as e:
            flog and flog.log(f"다운로드 실패: {e}")
            return None
    return root if _has_tools(root) else None


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


def wait_bootloader(timeout=10.0, callback=None, flog=None, hint="부트로더 대기"):
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
            time.sleep(0.4)
            return boot
        time.sleep(0.15)
    return None


# ─── 시리얼 '!' 부트로더 진입 (WDT 펌 정상 경로) ───────────

def _enter_bootloader_serial_cmd(port, flog=None):
    """9600으로 열어 '!' 전송 → 펌웨어 enterBootloader().
    DDONG-WDT2 이상에서만 동작. 옛 펌이면 무시되고 부트로더 안 뜸."""
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
        time.sleep(0.15)
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
    flog and flog.log("touch: serial '!' bootloader cmd OK")


# ─── 자동 1200bps 리셋 (옛 펌/비WDT 폴백) ─────────────────

def _touch_pyserial_hold(port, flog=None):
    """포트를 1200으로 0.5초 이상 열어 Windows가 SET_LINE_CODING을 보내게 함."""
    s = serial.Serial()
    s.port = port
    s.baudrate = 1200
    s.timeout = 0.1
    s.dsrdtr = False
    s.rtscts = False
    s.open()
    try:
        s.dtr = False
    except Exception:
        pass
    time.sleep(0.6)  # 핵심: 바로 닫지 말 것
    s.close()
    flog and flog.log("touch: pyserial hold-1200 OK")


def _touch_pyserial_reopen(port, flog=None):
    """9600으로 연 뒤 1200으로 재설정."""
    s = serial.Serial(port, 9600, timeout=0.1)
    time.sleep(0.15)
    s.close()
    time.sleep(0.15)
    s = serial.Serial()
    s.port = port
    s.baudrate = 1200
    s.dsrdtr = False
    s.open()
    try:
        s.dtr = False
    except Exception:
        pass
    time.sleep(0.5)
    s.close()
    flog and flog.log("touch: pyserial reopen 9600→1200 OK")


def _touch_powershell(port, flog=None):
    """System.IO.Ports.SerialPort — pyserial이 안 먹을 때 Windows 네이티브."""
    # COM10 이상은 \\.\COM10 형식 필요하지만 .NET SerialPort는 COM5 OK
    ps = f"""
$port = New-Object System.IO.Ports.SerialPort '{port}',1200,None,8,One
$port.DtrEnable = $false
$port.RtsEnable = $false
$port.ReadTimeout = 100
$port.WriteTimeout = 100
$port.Open()
Start-Sleep -Milliseconds 600
$port.Close()
$port.Dispose()
"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    )
    flog and flog.log(f"touch: powershell rc={r.returncode} err={(r.stderr or '')[:200]!r}")
    if r.returncode != 0:
        raise RuntimeError(r.stderr or "powershell touch fail")


def _touch_win32(port, flog=None):
    """CreateFile + SetCommState(1200)."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class DCB(ctypes.Structure):
        _fields_ = [
            ("DCBlength", wintypes.DWORD),
            ("BaudRate", wintypes.DWORD),
            ("fBinary", wintypes.DWORD, 1),
            ("fParity", wintypes.DWORD, 1),
            ("fOutxCtsFlow", wintypes.DWORD, 1),
            ("fOutxDsrFlow", wintypes.DWORD, 1),
            ("fDtrControl", wintypes.DWORD, 2),
            ("fDsrSensitivity", wintypes.DWORD, 1),
            ("fTXContinueOnXoff", wintypes.DWORD, 1),
            ("fOutX", wintypes.DWORD, 1),
            ("fInX", wintypes.DWORD, 1),
            ("fErrorChar", wintypes.DWORD, 1),
            ("fNull", wintypes.DWORD, 1),
            ("fRtsControl", wintypes.DWORD, 2),
            ("fAbortOnError", wintypes.DWORD, 1),
            ("fDummy2", wintypes.DWORD, 17),
            ("wReserved", wintypes.WORD),
            ("XonLim", wintypes.WORD),
            ("XoffLim", wintypes.WORD),
            ("ByteSize", ctypes.c_byte),
            ("Parity", ctypes.c_byte),
            ("StopBits", ctypes.c_byte),
            ("XonChar", ctypes.c_char),
            ("XoffChar", ctypes.c_char),
            ("ErrorChar", ctypes.c_char),
            ("EofChar", ctypes.c_char),
            ("EvtChar", ctypes.c_char),
            ("wReserved1", wintypes.WORD),
        ]

    path = f"\\\\.\\{port}"
    handle = kernel32.CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None
    )
    if handle == INVALID_HANDLE_VALUE or handle == -1:
        raise OSError(f"CreateFile failed for {path} err={ctypes.get_last_error()}")
    try:
        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        if not kernel32.GetCommState(handle, ctypes.byref(dcb)):
            raise OSError("GetCommState failed")
        dcb.BaudRate = 1200
        dcb.ByteSize = 8
        dcb.Parity = 0
        dcb.StopBits = 0
        dcb.fDtrControl = 0  # DTR_CONTROL_DISABLE
        if not kernel32.SetCommState(handle, ctypes.byref(dcb)):
            raise OSError("SetCommState 1200 failed")
        time.sleep(0.6)
    finally:
        kernel32.CloseHandle(handle)
    flog and flog.log("touch: win32 SetCommState 1200 OK")


def auto_enter_bootloader(port, callback=None, flog=None):
    """리셋버튼 없이 부트로더(PID 0036) 진입 시도. 성공 시 boot COM 반환.
    1순위: 시리얼 '!' (WDT2). 이후 1200bps 폴백(비WDT/옛 펌)."""
    methods = [
        ("serial-bang", _enter_bootloader_serial_cmd),
        ("pyserial-hold", _touch_pyserial_hold),
        ("powershell", _touch_powershell),
        ("win32", _touch_win32),
        ("pyserial-reopen", _touch_pyserial_reopen),
    ]
    for name, fn in methods:
        boot = find_bootloader_port()
        if boot:
            flog and flog.log(f"이미 부트로더: {boot}")
            return boot
        flog and flog.section(f"자동리셋 시도: {name}")
        if callback:
            callback(20, f"자동리셋: {name}")
        try:
            fn(port, flog=flog)
        except Exception as e:
            flog and flog.log(f"{name} 예외: {e!r}")
            continue
        # '!' 는 USB 재열거가 빨라 짧게, 1200은 조금 더
        wait_s = 6.0 if name == "serial-bang" else 8.0
        boot = wait_bootloader(timeout=wait_s, callback=callback, flog=flog, hint=f"{name} 후")
        if boot:
            flog and flog.log(f"성공: {name} → {boot}")
            return boot
        newport = find_arduino(preferred=port)
        if newport and newport != port:
            flog and flog.log(f"COM 변경 {port} → {newport}, 재시도 준비")
            port = newport
        # '!' 직후 COM이 잠깐 사라졌다가 스케치로 돌아올 수 있음
        if name == "serial-bang":
            time.sleep(0.5)
            newport = find_arduino(preferred=port)
            if newport:
                port = newport
    return None


# ─── arduino-cli 자동 설치/업로드 ─────────────────────────

def ensure_arduino_cli(flog=None, callback=None):
    exe = os.path.join(CLI_DIR, "arduino-cli.exe")
    if os.path.isfile(exe):
        flog and flog.log(f"arduino-cli 있음: {exe}")
        return exe
    os.makedirs(CLI_DIR, exist_ok=True)
    zip_path = os.path.join(TMP_ROOT, "arduino-cli.zip")
    if callback:
        callback(12, "arduino-cli 다운로드 중...")
    flog and flog.log(f"arduino-cli 다운로드: {CLI_ZIP_URL}")
    try:
        req = urllib.request.Request(CLI_ZIP_URL, headers={"User-Agent": "ddong"})
        with urllib.request.urlopen(req, timeout=180, context=_ssl_ctx()) as r:
            data = r.read()
        with open(zip_path, "wb") as f:
            f.write(data)
        flog and flog.log(f"zip size={len(data)}")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(CLI_DIR)
        # zip 안에 바로 exe 또는 하위폴더
        if not os.path.isfile(exe):
            for root, _, files in os.walk(CLI_DIR):
                if "arduino-cli.exe" in files:
                    src = os.path.join(root, "arduino-cli.exe")
                    if src != exe:
                        import shutil
                        shutil.copy2(src, exe)
                    break
        if os.path.isfile(exe):
            return exe
    except Exception as e:
        flog and flog.log(f"arduino-cli 설치 실패: {e!r}")
    return None


def ensure_avr_core(cli, flog=None, callback=None):
    try:
        if callback:
            callback(15, "Arduino AVR 코어 확인...")
        r = subprocess.run(
            [cli, "core", "list"],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        flog and flog.log(f"core list rc={r.returncode} out={(r.stdout or '')[:300]!r}")
        if "arduino:avr" in (r.stdout or ""):
            return True
        if callback:
            callback(16, "AVR 코어 설치 중(최초 1회)...")
        subprocess.run(
            [cli, "core", "update-index"],
            capture_output=True,
            timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        r2 = subprocess.run(
            [cli, "core", "install", "arduino:avr"],
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        flog and flog.log(f"core install rc={r2.returncode} {(r2.stdout or r2.stderr or '')[:400]!r}")
        return r2.returncode == 0
    except Exception as e:
        flog and flog.log(f"core 설치 예외: {e!r}")
        return False


def flash_via_arduino_cli(hex_path, port, flog=None, callback=None):
    cli = ensure_arduino_cli(flog=flog, callback=callback)
    if not cli:
        return False, "arduino-cli 확보 실패"
    ensure_avr_core(cli, flog=flog, callback=callback)
    if callback:
        callback(40, "arduino-cli 업로드...")
    cmd = [
        cli, "upload",
        "-p", port,
        "--fqbn", FQBN,
        "--input-file", hex_path,
        "-v",
    ]
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
            return False, "arduino-cli 90초 타임아웃"
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            line = line.rstrip()
            lines.append(line)
            flog and flog.log(f"  [cli] {line}")
            if callback and ("writing" in line.lower() or "upload" in line.lower()):
                callback(70, line[:70])
        elif proc.poll() is not None:
            break
        else:
            time.sleep(0.05)
    ok = proc.returncode == 0
    detail = lines[-1] if lines else f"code {proc.returncode}"
    return ok, detail


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


def flash(callback=None, port=None, ask_manual_reset=None):
    """자동 펌업 우선. return (ok, msg, log_path).
    1) 시리얼 '!' → avrdude  2) 1200/cli 폴백  3) 수동 더블리셋(최후, 1회 업그레이드용)
    """
    flog = FlashLogger()
    flog.section("펌업 시작 (시리얼'!' 우선, 1200은 폴백)")
    flog.log(f"python={sys.version}")
    flog.log(f"preferred={port!r}")
    flog.dump_ports("시작")

    try:
        if serial is None:
            msg = "pyserial 없음"
            return False, msg, flog.save(False, msg)

        _kill_stray_avrdude(flog)
        root = ensure_firmware(flog=flog, callback=callback)
        if not root:
            msg = "펌웨어 확보 실패"
            return False, msg, flog.save(False, msg)
        hex_path = os.path.join(root, HEX_NAME)
        flog.log(f"hex={hex_path} size={os.path.getsize(hex_path)}")

        com = find_arduino(preferred=port)
        if not com:
            msg = "아두이노 COM 없음"
            return False, msg, flog.save(False, msg)
        if callback:
            callback(10, f"장치: {com}")

        # 시리얼 핸들 완전 해제 (제어판이 포트 닫은 뒤)
        time.sleep(1.5)

        # 1) '!' / 1200 → 부트로더면 avrdude
        boot = auto_enter_bootloader(com, callback=callback, flog=flog)
        if boot:
            ok, detail = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
            if ok:
                if callback:
                    callback(100, "업로드 완료!")
                return True, f"완료(자동/{boot})", flog.save(True, f"완료(자동/{boot})")
            flog.log(f"avrdude 실패: {detail}")

        # 2) arduino-cli (비WDT/옛 펌 폴백 — WDT 펌에선 보통 실패)
        flog.section("arduino-cli 자동 업로드")
        com2 = find_arduino(preferred=port) or com
        ok2, detail2 = flash_via_arduino_cli(hex_path, com2, flog=flog, callback=callback)
        if ok2:
            if callback:
                callback(100, "업로드 완료!(cli)")
            return True, "완료(arduino-cli)", flog.save(True, "완료(arduino-cli)")
        flog.log(f"arduino-cli 실패: {detail2}")

        # 3) 최후: 옛 WDT 펌→WDT2 1회 업그레이드용 수동 (버튼 있는 보드)
        if callable(ask_manual_reset):
            flog.section("최후: 수동 더블리셋 (옛펌→WDT2 1회 / 버튼 있는 보드)")
            if callback:
                callback(25, "자동 실패 → 수동 안내")
            try:
                go = bool(ask_manual_reset())
            except Exception:
                go = False
            if go:
                boot = wait_bootloader(timeout=15.0, callback=callback, flog=flog, hint="수동리셋 대기")
                if boot:
                    ok3, detail3 = _run_avrdude(root, hex_path, boot, callback=callback, flog=flog)
                    if ok3:
                        if callback:
                            callback(100, "업로드 완료!")
                        return True, f"완료(수동/{boot})", flog.save(True, f"완료(수동/{boot})")

        msg = (
            "자동 펌업 실패.\n"
            "· WDT 펌은 1200bps 자동리셋이 안 됩니다.\n"
            "· 새 펌(DDONG-WDT2)이면 '!' 로 들어가야 하는데 부트로더가 안 떴습니다.\n"
            "· 옛 WDT 펌이면 리셋버튼 있는 보드에서 1회 수동 더블리셋으로 WDT2를 올려야 이후 자동됩니다.\n"
            f"· cli: {detail2}\n"
            f"로그: {FLASH_LOG}"
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
