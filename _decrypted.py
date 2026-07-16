import sys
import subprocess

def install_requirements():
    try:
        import customtkinter
        import mss
        import keyboard
        import serial
        import win32gui  
    except ImportError:
        print("\n[안내] 뚱시스템 구동에 필요한 필수 모듈이 누락되어 자동 설치를 시작합니다.")
        print("[안내] PC 환경에 따라 1~2분 정도 소요될 수 있습니다. 잠시만 기다려주세요...\n")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "numpy", "keyboard", "pyserial", "mss", "pillow", "cryptography", "customtkinter", "pywin32"])
            print("\n[완료] 모듈 설치가 성공적으로 끝났습니다! 시스템을 가동합니다.\n")
        except Exception as e:
            print(f"\n[오류] 자동 설치 중 문제가 발생했습니다: {e}")
            sys.exit(1)

install_requirements()

import time
import keyboard
import serial
import serial.tools.list_ports
import random
# import dxcam  # mss 전용으로 전환 — dxcam 네이티브 크래시 방지
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Lock
import ctypes 
import os 
from datetime import datetime 
import uuid
import hashlib
import urllib.request
import math
from PIL import Image, ImageTk
import customtkinter as ctk
import atexit 
import win32gui, win32con
import cv2
import numpy as np
import socket
import struct
import json

try:
    import kmNet
except ImportError:
    kmNet = None

try:
    import comtypes
    if hasattr(comtypes, '_compointer_base'):
        orig_del = comtypes._compointer_base.__del__
        def safe_del(self):
            try:
                if orig_del: orig_del(self)
            except: pass
        comtypes._compointer_base.__del__ = safe_del
    if hasattr(comtypes, 'IUnknown'):
        if hasattr(comtypes.IUnknown, '__del__'):
            orig_del_iunknwn = comtypes.IUnknown.__del__
            def safe_del_iunknwn(self):
                try:
                    if orig_del_iunknwn: orig_del_iunknwn(self)
                except: pass
            comtypes.IUnknown.__del__ = safe_del_iunknwn
        if hasattr(comtypes.IUnknown, 'Release'):
            orig_release_iunknwn = comtypes.IUnknown.Release
            def safe_release_iunknwn(self):
                try:
                    if orig_release_iunknwn: return orig_release_iunknwn(self)
                except: return 0
            comtypes.IUnknown.Release = safe_release_iunknwn
except: pass

try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

def get_hwid():
    mac = str(uuid.getnode())
    return hashlib.md5(mac.encode()).hexdigest()[:8].upper()

MY_HWID = get_hwid()

def auto_find_arduino():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if p.hwid and ("046D" in p.hwid.upper()) and ("C08B" in p.hwid.upper()): return p.device
    for p in ports:
        if p.hwid and ("2341" in p.hwid.upper()): return p.device
    for p in ports:
        if "CH340" in p.description or "Arduino" in p.description or "USB" in p.description or "직렬" in p.description: return p.device
    return ""

GOOGLE_SHEET_ID = "1FJznTKvy_4rnYkt9fI8u93MMow2she0AIlxmTWJz9XE"
GAS_API_URL = "https://script.google.com/macros/s/AKfycbwvgEjdco_Gtz4zH1anlpVRNzK2YkZb0Nhx8VLq06adMXsmElBJ8vfAUxh7Ay0bl3he/exec"

MY_PLAY_KEY = "1137"         
AUTH_FILE = "license.dat"
COORD_FILE = "saved_coord.txt"

SERIAL_PORT = auto_find_arduino()
if not SERIAL_PORT: SERIAL_PORT = 'COM5'
BAUD_RATE = 9600

# ── 하드웨어 선택 (아두이노 / KMBox) ──
HW_MODE = "뚱USB"          # license.dat에서 로드됨. 드롭다운으로 변경 (뚱USB=아두이노 / 뚱박스=KMBox)
_reconnect_req = False       # 드롭다운으로 장치 바꾸면 True → 워커가 재연결
_logo_frames = []            # 뚱박스 LCD 로고 프레임 (BGR flatten)
_logo_delay = 0.08           # 프레임 간격(초)

# ── KMBox Net 접속 설정 (아두이노 대체 하드웨어) ──
KM_IP = '192.168.2.188'
KM_PORT = '8808'
KM_MAC = 'c9fcdc04'


# ── 커스텀 토글 박스 ──
class RoundedToggle(ctk.CTkFrame):
    def __init__(self, parent, text, color, var=None, cmd=None):
        super().__init__(parent, fg_color="transparent")
        self.on_color = color; self.off_color = "#484f5a"
        self.var = var if var else tk.BooleanVar(value=True)
        self.initial = var.get() if var else True
        self.box = ctk.CTkFrame(self, width=18, height=18, fg_color=color if self.initial else self.off_color, corner_radius=4)
        self.box.pack(side="left", padx=(0,3))
        self.lbl = ctk.CTkLabel(self, text=text, font=("Malgun Gothic",9,"bold"), text_color="#cdd6f4")
        self.lbl.pack(side="left")
        self.box.bind("<Button-1>", self._toggle); self.lbl.bind("<Button-1>", self._toggle)
        self.cmd = cmd
        # 외부에서 var 변경 시 시각적 동기화
        self._trace_id = self.var.trace_add("write", self._sync)
    def _sync(self, *a):
        self.box.configure(fg_color=self.on_color if self.var.get() else self.off_color)
    def _toggle(self, e=None):
        v = not self.var.get(); self.var.set(v)
        self.box.configure(fg_color=self.on_color if v else self.off_color)
        if self.cmd: self.cmd()
    def get(self): return self.var.get()
    def set(self, v): self.var.set(v); self.box.configure(fg_color=self.on_color if v else self.off_color)


class Collapsible(ctk.CTkFrame):
    """▶/▼ 접이식 섹션 (뚱헌터 Collapsible과 동일 개념)."""
    def __init__(self, parent, title, start_open=False, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._title = title
        self._open = start_open
        self.btn = ctk.CTkButton(
            self, text=self._btn_text(), height=22, fg_color="#313244", hover_color="#45475a",
            anchor="w", font=("Malgun Gothic", 9, "bold"), text_color="#cdd6f4",
            command=self._flip,
        )
        self.btn.pack(fill="x", padx=2, pady=1)
        self.body = ctk.CTkFrame(self, fg_color="#313244", corner_radius=6)
        if start_open:
            self.body.pack(fill="x", padx=2, pady=(0, 2))

    def _btn_text(self):
        return f"{'▼' if self._open else '▶'} {self._title}"

    def _flip(self):
        self._open = not self._open
        self.btn.configure(text=self._btn_text())
        if self._open:
            self.body.pack(fill="x", padx=2, pady=(0, 2))
        else:
            self.body.pack_forget()
        top = self.winfo_toplevel()
        if top and top.winfo_exists():
            top.after(50, lambda: top.update_idletasks())


BUFF_SLOT_LABELS = ["F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
BUFF_SLOT_KEYS = {"F5": "5", "F6": "6", "F7": "7", "F8": "8", "F9": "9", "F10": "X", "F11": "Y", "F12": "Z"}
BUFF_HOTBARS = ["F1", "F2", "F3"]
_buff_cfg = {}
last_buff_times = {}
buff_next_due = {}
last_buff_global = 0
saved_buff_on = "0"
saved_buff_grid = {}
chk_buff_on = None
buff_hotbar_var = None


def buff_grid_key(hb, slot):
    return f"{hb}_{slot}"


def buff_time_key(hb, slot):
    return f"_buff_{hb}_{slot}"


def cast_buff(hb_label, slot_label):
    hb = hb_label.replace("F", "")
    sk = BUFF_SLOT_KEYS[slot_label]
    if hb == "1":
        execute_keys([sk], 0.5)
    else:
        execute_keys([hb, sk, "1"], 0.5)


def buff_interval_jitter(base_sec):
    """설정 초 ± 랜덤 (기계적 1200초 고정 방지)."""
    base = max(5, int(base_sec))
    spread = max(12, min(240, int(base * 0.14)))
    return max(8, int(base + human_delay(-spread, spread)))


def schedule_buff(tk, base_iv, soon=False):
    global buff_next_due
    if soon:
        buff_next_due[tk] = time.time() + human_delay(3, 18)
    else:
        buff_next_due[tk] = time.time() + buff_interval_jitter(base_iv)


def migrate_legacy_buffs():
    """예전 V_BL/V_SH/V_BLU/V_F10/V_F11 설정을 그리드로 이전."""
    global saved_buff_grid
    if saved_buff_grid:
        return
    legacy = [
        ("F2", "F5", saved_v_bl),
        ("F2", "F6", saved_v_sh),
        ("F2", "F11", saved_v_blu),
        ("F1", "F10", saved_v_f10),
        ("F1", "F11", saved_v_f11),
    ]
    for hb, slot, iv in legacy:
        try:
            sec = int(iv)
        except Exception:
            sec = 300
        if sec > 0:
            saved_buff_grid[buff_grid_key(hb, slot)] = f"0:{sec}"


PARTY_COORDS = [
    [348, 611], [268, 646], [264, 612],  
    [340, 612], [347, 645], [276, 678], [347, 678], [347, 711]
]
PARTY_ROIS = [(0,0,0,0)] * 8
PARTY_HP_THRESHOLDS = [50] * 8
PARTY_USE_ROI = [True] * 8
PARTY_HP_100_REF = [None] * 8
MAIN_ATTACKER_COORD = PARTY_COORDS[1] 

SELF_HP_COORD = [512, 591] 
SELF_HP_RGB = [74, 69, 78]
SELF_HP_ROI = (0,0,0,0)
SELF_HP_100_REF = None
self_hp_threshold = 30

NOPARTY_HP_COORD = [1040, 111]
NOPARTY_RGB = [162, 146, 150]
attacker_hp_threshold = 85.0
UDP_ATTACKER_PORT = 9999
attacker_hp_udp = 100.0
attacker_poisoned = False
attacker_petrified = False
last_udp_time = 0
last_auth_check = 0

DANGER_HP_COORD = [594, 593] 
DANGER_HP_RGB = [78, 69, 74]
DANGER_HP_ROI = (0,0,0,0)
DANGER_HP_100_REF = None
danger_hp_threshold = 20

MNA_ROI = (0,0,0,0)
MNA_100_REF = None
mna_threshold = 30
strong_heal_pct = 30
chk_strong_heal = None
last_mna_potion = 0
chk_mna = None

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ddong.log")
last_log = ""
log_history = []
def log_event(msg):
    global last_log
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    log_history.append(line)
    if len(log_history) > 50: log_history.pop(0)
    last_log = "\n".join(log_history[-8:])
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except: pass

SELF_POISON_COORD = [504, 589]
SELF_POISON_RGB = [10, 81, 0]
TARGET_POISON_COORD = [1000, 100] 
TARGET_POISON_RGB = [10, 81, 0]

BUFF_BAR_X1, BUFF_BAR_Y1, BUFF_BAR_X2, BUFF_BAR_Y2 = 0, 0, 0, 0
buff_templates = {}
buff_template_hu = {}

camera = None
ser = None


class KmBox:
    """아두이노 시리얼 대체 하드웨어. serial.Serial 호환 인터페이스(.write/.is_open/.flush/.close).
    아두이노코드.txt 펌웨어의 바이트 프로토콜을 그대로 kmNet 호출로 변환한다."""
    FKEY = {'1': 0x3A, '2': 0x3B, '3': 0x3C, '4': 0x3D, '5': 0x3E, '6': 0x3F,
            '7': 0x40, '8': 0x41, '9': 0x42, 'X': 0x43, 'Y': 0x44, 'Z': 0x45}
    SHIFT = 0xE1

    def __init__(self, ip, port, mac):
        if kmNet is None:
            raise RuntimeError("kmNet 모듈(pyd) 없음")
        r = kmNet.init(ip, port, mac)
        if r != 0:
            raise RuntimeError("뚱박스 연결 실패(%s)" % r)
        self.is_open = True
        self._buf = b""
        self._auto = False
        self._alive = True
        self._lk = Lock()
        Thread(target=self._auto_loop, daemon=True).start()

    # 자동클릭 루프 (펌웨어 loop()의 autoClick 재현: 30~75ms 누름, 85~180ms 간격)
    def _auto_loop(self):
        while self._alive:
            if self._auto and self.is_open:
                with self._lk:
                    try:
                        kmNet.left(1); time.sleep(random.uniform(0.030, 0.075)); kmNet.left(0)
                    except: pass
                time.sleep(random.uniform(0.085, 0.180))
            else:
                time.sleep(0.005)

    # 펌웨어 humanPress: 누르고 80~150ms 유지 후 뗌
    def _human_press(self, vk):
        with self._lk:
            try:
                kmNet.keydown(vk); time.sleep(random.uniform(0.080, 0.150)); kmNet.keyup(vk)
            except: pass

    def move_smooth(self, dx, dy, ms):
        """하드웨어 부드러운 이동(move_auto). 박스가 ms 동안 직선을 보간 → 뚝뚝거림 제거.
        move_auto 미지원 pyd면 False 반환(호출측이 기존 스텝방식으로 폴백)."""
        if not self.is_open or kmNet is None: return False
        dx, dy = int(dx), int(dy)
        if dx == 0 and dy == 0: return True
        fn = getattr(kmNet, "enc_move_auto", None) or getattr(kmNet, "move_auto", None)
        if fn is None: return False
        with self._lk:
            try: fn(dx, dy, int(ms))
            except: return False
        return True

    def write(self, data):
        if not self.is_open or kmNet is None: return
        if isinstance(data, str): data = data.encode()
        self._buf += data
        while self._buf:
            c = self._buf[:1]
            if c == b'<':                          # <dx,dy> 마우스 이동
                end = self._buf.find(b'>')
                if end == -1: return               # 토큰 미완성 → 다음 write 대기
                token = self._buf[1:end].decode(errors='ignore')
                self._buf = self._buf[end + 1:]
                try:
                    xs, ys = token.split(',')
                    with self._lk: kmNet.move(int(xs), int(ys))
                except: pass
            else:
                self._buf = self._buf[1:]
                self._cmd(chr(c[0]))

    def _cmd(self, cmd):
        if cmd == 'K':                             # 좌클릭 20~50ms
            with self._lk:
                try: kmNet.left(1); time.sleep(random.uniform(0.020, 0.050)); kmNet.left(0)
                except: pass
            return
        if cmd == 'U':                             # 자동클릭 OFF + 전체키 해제
            self._auto = False
            with self._lk:
                try: kmNet.keyup(self.SHIFT)
                except: pass
            return
        if cmd == 'H':                             # Shift 누름 유지 + 자동클릭 ON
            with self._lk:
                try: kmNet.keydown(self.SHIFT)
                except: pass
            self._auto = True
            return
        if cmd == 'R':                             # Shift 뗌 + 자동클릭 OFF
            with self._lk:
                try: kmNet.keyup(self.SHIFT)
                except: pass
            self._auto = False
            return
        if cmd == 'T':                             # 자동클릭 토글
            self._auto = not self._auto
            return
        if cmd == 'A':                             # F9
            self._human_press(0x42); return
        if cmd == 'B':                             # F9 두 번
            self._human_press(0x42); time.sleep(random.uniform(0.070, 0.130)); self._human_press(0x42); return
        if cmd == 'E':                             # F5
            self._human_press(0x3E); return
        if cmd == 'C':                             # 자동클릭OFF + 전체해제 + F8 1.1~1.4초 꾹
            self._auto = False
            with self._lk:
                try:
                    kmNet.keyup(self.SHIFT); time.sleep(0.01); kmNet.keydown(0x41)
                    time.sleep(random.uniform(1.1, 1.4)); kmNet.keyup(0x41)
                except: pass
            return
        if cmd in self.FKEY:                        # 1~9,X,Y,Z → F1~F12
            self._human_press(self.FKEY[cmd]); return

    def flush(self): pass

    def lcd(self, frame):
        # LCD에 이미지 프레임 표시 (봇 명령이랑 같은 Lock으로 순서 보장)
        if not self.is_open or kmNet is None or not hasattr(kmNet, "lcd_picture"): return
        with self._lk:
            try: kmNet.lcd_picture(frame)
            except: pass

    def close(self):
        self._alive = False
        self._auto = False
        try: kmNet.keyup(self.SHIFT)
        except: pass
        self.is_open = False


running = False
BASE_BUFF_INTERVAL = 300
BUFF_SEQ_GAP = 5.0
last_loot = 0
last_buff_seq = 0
last_loot_sent_time = 0
loot_interval = 5.0
debounce = {'caps': 0, 'tab': 0, 'main': 0, 'space': 0, 'f4': 0}
current_f9_prob = 0.3
last_self_heal = 0
last_party_heal = 0
last_party_cure = 0
last_noparty_heal = 0

selected_party_flags = [0, 1, 0, 0, 0, 0, 0, 0]
saved_party_flags = "0,1,0,0,0,0,0,0"
party_mode_flags = [1, 1, 1, 1, 1, 1, 1, 1]
saved_party_mode_flags = "1,1,1,1,1,1,1,1"

saved_v_bl = "1800"
saved_v_sh = "1200"
saved_v_blu = "1200"
saved_v_f10 = "1200"
saved_v_f11 = "1200"
saved_expire_start = ""
saved_expire_days = "0"

root = None
chk_fix = None
chk_follow = None
chk_space_save = None
mode_var = None
chk_poison = None
chk_target_poison = None
chk_party_poison = None
chk_loot = None
lbl_status = None
lbl_buff = None
lbl_saved_coord = None
lbl_coords = None
lbl_ard = None

shutdown_time = None
timer_thread_active = False

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

def check_google_sheet(input_code):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode('utf-8-sig', errors='ignore').splitlines()
        for i, line in enumerate(data):
            if i == 0: continue 
            cols = [c.strip('"') for c in line.split(',')]
            if len(cols) >= 1:
                db_code = cols[0].strip()
                db_hwid = cols[1].strip() if len(cols) >= 2 else ""
                db_expire = cols[2].strip() if len(cols) >= 3 else ""
                db_start = cols[3].strip() if len(cols) >= 4 else ""
                if input_code == db_code:
                    if not db_hwid or db_hwid == "":
                        return "REGISTER", db_expire, db_start
                    if db_hwid == "ANY":
                        return "PASS", db_expire, db_start
                    if db_hwid != MY_HWID:
                        return "ALREADY_IN_USE", "", ""
                    return "PASS", db_expire, db_start
        return "NOT_FOUND", "", "" 
    except:
        return "ERROR", "", ""

def load_hidden_config():
    global MAIN_ATTACKER_COORD, SELF_HP_COORD, SELF_HP_RGB, NOPARTY_HP_COORD, NOPARTY_RGB, PARTY_COORDS
    global SELF_POISON_COORD, SELF_POISON_RGB, TARGET_POISON_COORD, TARGET_POISON_RGB, DANGER_HP_COORD, DANGER_HP_RGB
    global saved_v_bl, saved_v_sh, saved_v_blu, saved_v_f10, saved_v_f11
    global saved_buff_on, saved_buff_grid
    global BUFF_BAR_X1, BUFF_BAR_Y1, BUFF_BAR_X2, BUFF_BAR_Y2
    global saved_expire_start, saved_expire_days
    global saved_party_flags, saved_party_mode_flags
    global SELF_HP_ROI, SELF_HP_100_REF, DANGER_HP_ROI, DANGER_HP_100_REF
    global MNA_ROI, MNA_100_REF, mna_threshold
    global self_hp_threshold, danger_hp_threshold, attacker_hp_threshold
    global PARTY_ROIS, PARTY_HP_100_REF, PARTY_HP_THRESHOLDS, PARTY_USE_ROI
    
    text_value_keys = {"V_BL", "V_SH", "V_BLU", "V_F10", "V_F11", "EXPIRE_START", "EXPIRE_DAYS",
                       "PARTY_FLAGS", "PARTY_MODE_FLAGS", "BUFF_ON"}
    saved_pwd = None
    saved_expire_start = ""
    saved_expire_days = "0"
    saved_buff_on = "0"
    saved_buff_grid = {}
    
    if os.path.exists(AUTH_FILE):
        ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 2)
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f: lines = f.readlines()
            if not lines: return None
            saved_pwd = lines[0].strip() 
            text_key_map = {
                "V_BL": "saved_v_bl", "V_SH": "saved_v_sh", "V_BLU": "saved_v_blu",
                "V_F10": "saved_v_f10", "V_F11": "saved_v_f11",
                "EXPIRE_START": chr(115)+chr(97)+chr(118)+chr(101)+chr(100)+chr(95)+chr(101)+chr(120)+chr(112)+chr(105)+chr(114)+chr(101)+chr(95)+chr(115)+chr(116)+chr(97)+chr(114)+chr(116),
                "EXPIRE_DAYS": chr(115)+chr(97)+chr(118)+chr(101)+chr(100)+chr(95)+chr(101)+chr(120)+chr(112)+chr(105)+chr(114)+chr(101)+chr(95)+chr(100)+chr(97)+chr(121)+chr(115),
                "PARTY_FLAGS": "saved_party_flags", "PARTY_MODE_FLAGS": "saved_party_mode_flags",
                "BUFF_ON": "saved_buff_on",
            }
            coord_map = {
                "MAIN_ATTACKER_X": (MAIN_ATTACKER_COORD, 0), "MAIN_ATTACKER_Y": (MAIN_ATTACKER_COORD, 1),
                "SELF_HP_X": (SELF_HP_COORD, 0), "SELF_HP_Y": (SELF_HP_COORD, 1),
                "SELF_HP_R": (SELF_HP_RGB, 0), "SELF_HP_G": (SELF_HP_RGB, 1), "SELF_HP_B": (SELF_HP_RGB, 2),
                "NOPARTY_X": (NOPARTY_HP_COORD, 0), "NOPARTY_Y": (NOPARTY_HP_COORD, 1),
                "NOPARTY_R": (NOPARTY_RGB, 0), "NOPARTY_G": (NOPARTY_RGB, 1), "NOPARTY_B": (NOPARTY_RGB, 2),
                "SELF_POISON_X": (SELF_POISON_COORD, 0), "SELF_POISON_Y": (SELF_POISON_COORD, 1),
                "SELF_POISON_R": (SELF_POISON_RGB, 0), "SELF_POISON_G": (SELF_POISON_RGB, 1), "SELF_POISON_B": (SELF_POISON_RGB, 2),
                "TARGET_POISON_X": (TARGET_POISON_COORD, 0), "TARGET_POISON_Y": (TARGET_POISON_COORD, 1),
                "TARGET_POISON_R": (TARGET_POISON_RGB, 0), "TARGET_POISON_G": (TARGET_POISON_RGB, 1), "TARGET_POISON_B": (TARGET_POISON_RGB, 2),
                "DANGER_HP_X": (DANGER_HP_COORD, 0), "DANGER_HP_Y": (DANGER_HP_COORD, 1),
                "DANGER_HP_R": (DANGER_HP_RGB, 0), "DANGER_HP_G": (DANGER_HP_RGB, 1), "DANGER_HP_B": (DANGER_HP_RGB, 2),
                "BUFF_BAR_X1": (None, 0), "BUFF_BAR_Y1": (None, 1), "BUFF_BAR_X2": (None, 2), "BUFF_BAR_Y2": (None, 3),
            }
            buff_bar_vals = [0, 0, 0, 0]
            self_roi_vals = [0, 0, 0, 0]
            danger_roi_vals = [0, 0, 0, 0]
            mna_roi_vals = [0, 0, 0, 0]
            party_roi_vals = [[0,0,0,0] for _ in range(8)]
            
            for line in lines[1:]:
                line = line.strip()
                if not line or "=" not in line: continue
                key, val = line.split('=', 1)
                val_str = val.strip()
                if key == "HW_MODE": globals()['HW_MODE'] = {"KMBox": "뚱박스", "아두이노": "뚱USB"}.get(val_str, val_str); continue
                if key == "KM_IP": globals()['KM_IP'] = val_str; continue
                if key == "KM_PORT": globals()['KM_PORT'] = val_str; continue
                if key == "KM_MAC": globals()['KM_MAC'] = val_str; continue
                if key in text_value_keys:
                    if key in text_key_map: globals()[text_key_map[key]] = val_str
                    continue
                if key.startswith("BUFF_") and key.count("_") >= 2:
                    # BUFF_F2_F5=1:1800
                    parts = key.split("_", 2)
                    if len(parts) == 3 and parts[1] in BUFF_HOTBARS and parts[2] in BUFF_SLOT_LABELS:
                        saved_buff_grid[f"{parts[1]}_{parts[2]}"] = val_str
                    continue
                if key == "SELF_HP_ROI_X1": self_roi_vals[0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_ROI_Y1": self_roi_vals[1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_ROI_X2": self_roi_vals[2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_ROI_Y2": self_roi_vals[3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "SELF_HP_100_REF": SELF_HP_100_REF = int(val_str) if val_str.lstrip('-').isdigit() else None; continue
                if key == "DANGER_HP_ROI_X1": danger_roi_vals[0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_ROI_Y1": danger_roi_vals[1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_ROI_X2": danger_roi_vals[2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_ROI_Y2": danger_roi_vals[3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "DANGER_HP_100_REF": DANGER_HP_100_REF = int(val_str) if val_str.lstrip('-').isdigit() else None; continue
                if key == "SELF_HP_THRESHOLD": self_hp_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 30; continue
                if key == "DANGER_HP_THRESHOLD": danger_hp_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 20; continue
                if key == "ATTACKER_HP_THRESHOLD": attacker_hp_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 85; continue
                if key == "MNA_ROI_X1": mna_roi_vals[0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_ROI_Y1": mna_roi_vals[1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_ROI_X2": mna_roi_vals[2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_ROI_Y2": mna_roi_vals[3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; continue
                if key == "MNA_100_REF": MNA_100_REF = int(val_str) if val_str.lstrip('-').isdigit() else None; continue
                if key == "MNA_THRESHOLD": mna_threshold = int(val_str) if val_str.lstrip('-').isdigit() else 30; continue
                for pi in range(8):
                    if key == f"PARTY_ROI_P{pi+1}_X1": party_roi_vals[pi][0] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_ROI_P{pi+1}_Y1": party_roi_vals[pi][1] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_ROI_P{pi+1}_X2": party_roi_vals[pi][2] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_ROI_P{pi+1}_Y2": party_roi_vals[pi][3] = int(val_str) if val_str.lstrip('-').isdigit() else 0; break
                    if key == f"PARTY_HP_100_REF_P{pi+1}": PARTY_HP_100_REF[pi] = int(val_str) if val_str.lstrip('-').isdigit() else None; break
                    if key == f"PARTY_HP_THR_P{pi+1}": PARTY_HP_THRESHOLDS[pi] = int(val_str) if val_str.lstrip('-').isdigit() else 50; break
                    if key == f"PARTY_USE_ROI_P{pi+1}": PARTY_USE_ROI[pi] = bool(int(val_str)) if val_str in ('0','1') else True; break
                try: val = int(val_str)
                except: continue
                if key in coord_map:
                    if key.startswith("BUFF_BAR"):
                        idx = {"BUFF_BAR_X1": 0, "BUFF_BAR_Y1": 1, "BUFF_BAR_X2": 2, "BUFF_BAR_Y2": 3}[key]
                        buff_bar_vals[idx] = val
                    else:
                        target_list, target_idx = coord_map[key]
                        target_list[target_idx] = val
                else:
                    for i in range(8):
                        if key == f"P{i+1}_X": PARTY_COORDS[i][0] = val
                        elif key == f"P{i+1}_Y": PARTY_COORDS[i][1] = val
        except: pass
        if buff_bar_vals[0] != 0: BUFF_BAR_X1 = buff_bar_vals[0]
        if buff_bar_vals[1] != 0: BUFF_BAR_Y1 = buff_bar_vals[1]
        if buff_bar_vals[2] != 0: BUFF_BAR_X2 = buff_bar_vals[2]
        if buff_bar_vals[3] != 0: BUFF_BAR_Y2 = buff_bar_vals[3]
        if self_roi_vals[0] != 0 or self_roi_vals[2] != 0: SELF_HP_ROI = tuple(self_roi_vals)
        if danger_roi_vals[0] != 0 or danger_roi_vals[2] != 0: DANGER_HP_ROI = tuple(danger_roi_vals)
        if mna_roi_vals[0] != 0 or mna_roi_vals[2] != 0: MNA_ROI = tuple(mna_roi_vals)
        for pi in range(8):
            if party_roi_vals[pi][0] != 0 or party_roi_vals[pi][2] != 0: PARTY_ROIS[pi] = tuple(party_roi_vals[pi])
        globals()["saved_buff_on"] = saved_buff_on
        globals()["saved_buff_grid"] = saved_buff_grid
    migrate_legacy_buffs()
    return saved_pwd

def save_hidden_config(pwd_to_save):
    try:
        def _buff_iv(hb, slot, default):
            if hb in _buff_cfg:
                for sl, _cb, iv in _buff_cfg[hb]:
                    if sl == slot:
                        return iv.get() if iv.get() else default
            return default

        cur_v_bl = _buff_iv("F2", "F5", saved_v_bl)
        cur_v_sh = _buff_iv("F2", "F6", saved_v_sh)
        cur_v_blu = _buff_iv("F2", "F11", saved_v_blu)
        cur_v_f10 = _buff_iv("F1", "F10", saved_v_f10)
        cur_v_f11 = _buff_iv("F1", "F11", saved_v_f11)
        cur_km_ip = ent_km_ip.get().strip() if ('ent_km_ip' in globals() and ent_km_ip and ent_km_ip.get().strip()) else KM_IP
        cur_km_port = ent_km_port.get().strip() if ('ent_km_port' in globals() and ent_km_port and ent_km_port.get().strip()) else KM_PORT
        cur_km_mac = ent_km_mac.get().strip() if ('ent_km_mac' in globals() and ent_km_mac and ent_km_mac.get().strip()) else KM_MAC
        cur_hw = hw_var.get() if ('hw_var' in globals() and hw_var) else HW_MODE
        globals()['KM_IP'] = cur_km_ip; globals()['KM_PORT'] = cur_km_port; globals()['KM_MAC'] = cur_km_mac; globals()['HW_MODE'] = cur_hw
        tmp_auth_file = AUTH_FILE + ".tmp"
        if os.path.exists(AUTH_FILE): ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 128)

        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            f.write(f"{pwd_to_save}\n")
            for key, value in [
                ("MAIN_ATTACKER_X", MAIN_ATTACKER_COORD[0]), ("MAIN_ATTACKER_Y", MAIN_ATTACKER_COORD[1]),
                # Self coord removed
                ("SELF_HP_R", SELF_HP_RGB[0]), ("SELF_HP_G", SELF_HP_RGB[1]), ("SELF_HP_B", SELF_HP_RGB[2]),
                ("NOPARTY_X", NOPARTY_HP_COORD[0]), ("NOPARTY_Y", NOPARTY_HP_COORD[1]),
                ("NOPARTY_R", NOPARTY_RGB[0]), ("NOPARTY_G", NOPARTY_RGB[1]), ("NOPARTY_B", NOPARTY_RGB[2]),
                ("SELF_POISON_X", SELF_POISON_COORD[0]), ("SELF_POISON_Y", SELF_POISON_COORD[1]),
                ("SELF_POISON_R", SELF_POISON_RGB[0]), ("SELF_POISON_G", SELF_POISON_RGB[1]), ("SELF_POISON_B", SELF_POISON_RGB[2]),
                ("TARGET_POISON_X", TARGET_POISON_COORD[0]), ("TARGET_POISON_Y", TARGET_POISON_COORD[1]),
                ("TARGET_POISON_R", TARGET_POISON_RGB[0]), ("TARGET_POISON_G", TARGET_POISON_RGB[1]), ("TARGET_POISON_B", TARGET_POISON_RGB[2]),
                # Danger coord removed
                ("DANGER_HP_R", DANGER_HP_RGB[0]), ("DANGER_HP_G", DANGER_HP_RGB[1]), ("DANGER_HP_B", DANGER_HP_RGB[2]),
            ]: f.write(f"{key}={value}\n")
            # Old PARTY_COORDS save removed
            for key, value in [("BUFF_BAR_X1", BUFF_BAR_X1), ("BUFF_BAR_Y1", BUFF_BAR_Y1), ("BUFF_BAR_X2", BUFF_BAR_X2), ("BUFF_BAR_Y2", BUFF_BAR_Y2)]:
                f.write(f"{key}={value}\n")
            for key, value in [("V_BL", cur_v_bl), ("V_SH", cur_v_sh), ("V_BLU", cur_v_blu), ("V_F10", cur_v_f10), ("V_F11", cur_v_f11)]:
                f.write(f"{key}={value}\n")
            cur_buff_on = "1" if (chk_buff_on and chk_buff_on.get()) else saved_buff_on
            f.write(f"BUFF_ON={cur_buff_on}\n")
            for hb in BUFF_HOTBARS:
                for slot in BUFF_SLOT_LABELS:
                    gk = buff_grid_key(hb, slot)
                    on_s, sec_s = "0", str(BASE_BUFF_INTERVAL)
                    if hb in _buff_cfg:
                        for sl, cb, iv in _buff_cfg[hb]:
                            if sl == slot:
                                on_s = "1" if cb.get() else "0"
                                sec_s = iv.get() if iv.get() else str(BASE_BUFF_INTERVAL)
                                break
                    elif gk in saved_buff_grid:
                        parts = saved_buff_grid[gk].split(":", 1)
                        if len(parts) == 2:
                            on_s, sec_s = parts[0], parts[1]
                    f.write(f"BUFF_{hb}_{slot}={on_s}:{sec_s}\n")
            f.write(f"HW_MODE={cur_hw}\nKM_IP={cur_km_ip}\nKM_PORT={cur_km_port}\nKM_MAC={cur_km_mac}\n")
            if saved_expire_start: f.write(f"EXPIRE_START={saved_expire_start}\n")
            f.write(f"EXPIRE_DAYS={saved_expire_days}\n")
            f.write(f"PARTY_FLAGS={saved_party_flags}\nPARTY_MODE_FLAGS={saved_party_mode_flags}\n")
            f.write(f"SELF_HP_ROI_X1={SELF_HP_ROI[0]}\nSELF_HP_ROI_Y1={SELF_HP_ROI[1]}\nSELF_HP_ROI_X2={SELF_HP_ROI[2]}\nSELF_HP_ROI_Y2={SELF_HP_ROI[3]}\n")
            if SELF_HP_100_REF is not None: f.write(f"SELF_HP_100_REF={SELF_HP_100_REF}\n")
            f.write(f"DANGER_HP_ROI_X1={DANGER_HP_ROI[0]}\nDANGER_HP_ROI_Y1={DANGER_HP_ROI[1]}\nDANGER_HP_ROI_X2={DANGER_HP_ROI[2]}\nDANGER_HP_ROI_Y2={DANGER_HP_ROI[3]}\n")
            if DANGER_HP_100_REF is not None: f.write(f"DANGER_HP_100_REF={DANGER_HP_100_REF}\n")
            f.write(f"SELF_HP_THRESHOLD={self_hp_threshold}\nDANGER_HP_THRESHOLD={danger_hp_threshold}\nATTACKER_HP_THRESHOLD={int(attacker_hp_threshold)}\n")
            f.write(f"MNA_ROI_X1={MNA_ROI[0]}\nMNA_ROI_Y1={MNA_ROI[1]}\nMNA_ROI_X2={MNA_ROI[2]}\nMNA_ROI_Y2={MNA_ROI[3]}\n")
            if MNA_100_REF is not None: f.write(f"MNA_100_REF={MNA_100_REF}\n")
            f.write(f"MNA_THRESHOLD={mna_threshold}\n")
            f.write(f"STRONG_HEAL_PCT={strong_heal_pct}\n")
            for pi in range(8):
                r = PARTY_ROIS[pi]
                f.write(f"PARTY_ROI_P{pi+1}_X1={r[0]}\nPARTY_ROI_P{pi+1}_Y1={r[1]}\nPARTY_ROI_P{pi+1}_X2={r[2]}\nPARTY_ROI_P{pi+1}_Y2={r[3]}\n")
                if PARTY_HP_100_REF[pi] is not None: f.write(f"PARTY_HP_100_REF_P{pi+1}={PARTY_HP_100_REF[pi]}\n")
                f.write(f"PARTY_HP_THR_P{pi+1}={PARTY_HP_THRESHOLDS[pi]}\nPARTY_USE_ROI_P{pi+1}={1 if PARTY_USE_ROI[pi] else 0}\n")
        ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 2)
        try:
            import base64, zlib
            src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(__file__))
            dst_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.txt")
            with open(src_path, "r", encoding="utf-8") as src: source = src.read()
            compressed = zlib.compress(source.encode("utf-8"))
            b64 = base64.b64encode(compressed).decode("utf-8")
            with open(dst_path, "w", encoding="utf-8") as dst: dst.write("".join(chr(ord(c) + 1) for c in b64))
        except: pass
    except: pass

loaded_pwd = load_hidden_config()

try:
    parts = saved_party_flags.split(',')
    if len(parts) == 8: selected_party_flags = [int(p.strip()) for p in parts]
    else: selected_party_flags = [0, 1, 0, 0, 0, 0, 0, 0]
except: selected_party_flags = [0, 1, 0, 0, 0, 0, 0, 0]

try:
    parts = saved_party_mode_flags.split(',')
    if len(parts) == 8: party_mode_flags = [int(p.strip()) for p in parts]
    else: party_mode_flags = [1,1,1,1,1,1,1,1]
except: party_mode_flags = [1,1,1,1,1,1,1,1]

def get_pixel_color_native(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    if color == -1: return 0, 0, 0
    return color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff

def ask_admin_pw():
    open_admin_panel()

def open_admin_panel():
    try:
        _open_admin_panel_impl()
    except Exception as e:
        import traceback
        ctypes.windll.user32.MessageBoxW(0, f"제어판 오류:\n{e}", "오류", 0x10)

def _open_admin_panel_impl():
    admin = ctk.CTkToplevel(root)
    admin.title("실시간 제어판")
    w, h = 520, 550
    sw = admin.winfo_screenwidth(); sh = admin.winfo_screenheight()
    admin.geometry(f"{w}x{h}+{int((sw-w)/2)}+{int((sh-h)/2)}")
    admin.attributes("-topmost", True)
    admin.focus_force() 
    admin.configure(fg_color="#181825")

    cap_data = {"x": 0, "y": 0, "r": 0, "g": 0, "b": 0}
    entries = {}

    def update_admin_live():
        if not admin.winfo_exists(): return
        if camera:
            try:
                if not admin.winfo_exists(): return
                frame = camera.get_latest_frame()
                if frame is not None:
                    for pi in range(8):
                        if PARTY_ROIS[pi][0] > 0:
                            hp_pct = scan_party_hp(frame, pi)
                            bar = entries[f"P{pi+1}_BAR"]
                            if hp_pct is None:
                                bar.set(0)
                                entries[f"P{pi+1}_PCT"].configure(text="없음", text_color="#6c7086")
                            else:
                                bar.set(hp_pct / 100.0)
                                bar.configure(progress_color="#ef4444" if hp_pct < PARTY_HP_THRESHOLDS[pi] else "#10b981")
                                entries[f"P{pi+1}_PCT"].configure(text=f"{int(hp_pct)}%", text_color="#ef4444" if hp_pct < PARTY_HP_THRESHOLDS[pi] else "#10b981")
            except: pass
        admin.after(500, update_admin_live)



    scrollable_frame = ctk.CTkScrollableFrame(admin, width=500, height=450, fg_color="#1e1e2e", corner_radius=8)

    def add_row(parent, label_text, prefix, vx, vy, vr=None, vg=None, vb=None, has_rgb=False, show_apply=True):
        row = ctk.CTkFrame(parent, fg_color="transparent"); row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label_text, width=95, anchor="w", text_color="#cba6f7", font=("Malgun Gothic", 11, "bold")).pack(side="left")
        ex = ctk.CTkEntry(row, width=38, height=22, fg_color="#313244", text_color="#cdd6f4", justify="center", font=("Malgun Gothic", 10))
        ex.insert(0, str(vx)); ex.pack(side="left", padx=1); entries[f"{prefix}_X"] = ex
        ey = ctk.CTkEntry(row, width=38, height=22, fg_color="#313244", text_color="#cdd6f4", justify="center", font=("Malgun Gothic", 10))
        ey.insert(0, str(vy)); ey.pack(side="left", padx=1); entries[f"{prefix}_Y"] = ey
        if has_rgb:
            ctk.CTkLabel(row, text="R:", text_color="#f38ba8", font=("Malgun Gothic", 9)).pack(side="left", padx=(3,1))
            er = ctk.CTkEntry(row, width=32, height=22, fg_color="#313244", text_color="#cdd6f4", justify="center", font=("Malgun Gothic", 10))
            er.insert(0, str(vr)); er.pack(side="left"); entries[f"{prefix}_R"] = er
            ctk.CTkLabel(row, text="G:", text_color="#a6e3a1", font=("Malgun Gothic", 9)).pack(side="left", padx=(3,1))
            eg = ctk.CTkEntry(row, width=32, height=22, fg_color="#313244", text_color="#cdd6f4", justify="center", font=("Malgun Gothic", 10))
            eg.insert(0, str(vg)); eg.pack(side="left"); entries[f"{prefix}_G"] = eg
            ctk.CTkLabel(row, text="B:", text_color="#89b4fa", font=("Malgun Gothic", 9)).pack(side="left", padx=(3,1))
            eb = ctk.CTkEntry(row, width=32, height=22, fg_color="#313244", text_color="#cdd6f4", justify="center", font=("Malgun Gothic", 10))
            eb.insert(0, str(vb)); eb.pack(side="left"); entries[f"{prefix}_B"] = eb
        if show_apply:
            ctk.CTkButton(row, text="적용", width=35, height=22, fg_color="#800020", hover_color="#9e1a3a", text_color="#ffffff", font=("Malgun Gothic", 10, "bold")).pack(side="right", padx=2)

    # --- ROI 미리보기 유틸 ---
    def refresh_preview(preview_label, roi_lbl, roi, ref100, is_blue=False, strict=True):
        if roi[0] == 0: return
        import mss as _mss
        sct = _mss.MSS()
        x1, y1, x2, y2 = roi
        img = sct.grab({"left": x1, "top": y1, "width": max(x2-x1,1), "height": max(y2-y1,1)})
        arr = np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
        try:
            h, w = arr.shape[:2]; pw = min(w*2, 180); ph = max(h, 3)
            pil_img = Image.fromarray(arr).resize((pw, ph), Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img); preview_label.config(image=photo); preview_label.image = photo
        except: pass
        if roi_lbl:
            if is_blue:
                Rq = arr[:,:,0].astype(int); Gq = arr[:,:,1].astype(int); Bq = arr[:,:,2].astype(int)
                blue = (Bq>50)&(Bq>Rq*1.1)&(Bq>Gq*1.1)
                raw = int(np.sum(blue)); wh = max(x2-x1,1)*max(y2-y1,1)
                pct = round(raw/ref100*100,1) if (ref100 and ref100>0) else round(raw/max(wh,1)*100,1)
                roi_lbl.configure(text=f"ROI=({x1},{y1},{x2-x1},{y2-y1}) | MP:{pct:.0f}% | 100%ref:{ref100 or '?'}px", text_color="#f0f0f0")
            else:
                if strict:
                    if not party_slot_active_rgb(arr):
                        roi_lbl.configure(text=f"ROI=({x1},{y1},{x2-x1},{y2-y1}) | 없음 (빈칸/사망)", text_color="#6c7086")
                    else:
                        pct = bar_fill_pct_from_rgb(arr, ref100, strict=True)
                        roi_lbl.configure(text=f"ROI=({x1},{y1},{x2-x1},{y2-y1}) | HP:{pct:.0f}% | 100%ref:{ref100 or '?'}col", text_color="#f0f0f0")
                else:
                    pct = _self_hp_pct_from_arr(arr, ref100)   # 쫄법 전용 — 파티 판정과 무관, 단순 열개수
                    roi_lbl.configure(text=f"ROI=({x1},{y1},{x2-x1},{y2-y1}) | HP:{pct:.0f}% | 100%ref:{ref100 or '?'}col", text_color="#f0f0f0")

    def open_self_hp_overlay():
        ov = tk.Toplevel(admin); ov.overrideredirect(True)
        sx = ctypes.windll.user32.GetSystemMetrics(76); sy = ctypes.windll.user32.GetSystemMetrics(77)
        sw = ctypes.windll.user32.GetSystemMetrics(78); sh = ctypes.windll.user32.GetSystemMetrics(79)
        ov.geometry(f"{sw}x{sh}+{sx}+{sy}"); ov.attributes("-alpha",0.35)
        ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
        cv = tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
        d = {"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
        def dn(e):
            d["x1"],d["y1"]=e.x_root,e.y_root
            d["r"]=cv.create_rectangle(e.x_root-sx,e.y_root-sy,e.x_root-sx,e.y_root-sy,
                        outline="#10b981", width=4)
        def mv(e):
            cv.coords(d["r"],d["x1"]-sx,d["y1"]-sy,e.x_root-sx,e.y_root-sy)
        def up(e):
            d["x2"],d["y2"]=e.x_root,e.y_root
            x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
            if x2-x1<8 or y2-y1<3: ov.destroy(); return
            global SELF_HP_ROI; SELF_HP_ROI=(x1,y1,x2,y2)
            save_hidden_config(loaded_pwd if (loaded_pwd) else "")
            ov.destroy()
            admin.after(300, lambda: refresh_preview(self_roi_preview,self_roi_lbl,SELF_HP_ROI,SELF_HP_100_REF,strict=False))
        cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
        tk.Label(ov,text="🟢 쫄법 피통 왼쪽→오른쪽 드래그",fg="#10b981",bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
        tk.Label(ov,text="ESC=취소",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
        ov.bind("<Escape>",lambda e:ov.destroy())

    def set_self_100ref():
        global SELF_HP_100_REF
        x1,y1,x2,y2=SELF_HP_ROI
        if x1==0 and x2==0: return
        import mss as _mss; sct = _mss.MSS()
        img = sct.grab({"left": x1, "top": y1, "width": max(x2-x1,1), "height": max(y2-y1,1)})
        arr = np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
        SELF_HP_100_REF = max(1, _self_hp_fill_cols(arr)[0])
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        messagebox.showinfo("100% 기준","[내피통] 저장됨: "+str(SELF_HP_100_REF)+"col")
        admin.after(300, lambda: refresh_preview(self_roi_preview,self_roi_lbl,SELF_HP_ROI,SELF_HP_100_REF,strict=False))

    def open_mna_roi_overlay():
        ov=tk.Toplevel(admin); ov.overrideredirect(True)
        sx3 = ctypes.windll.user32.GetSystemMetrics(76); sy3 = ctypes.windll.user32.GetSystemMetrics(77)
        sw3 = ctypes.windll.user32.GetSystemMetrics(78); sh3 = ctypes.windll.user32.GetSystemMetrics(79)
        ov.geometry(f"{sw3}x{sh3}+{sx3}+{sy3}"); ov.attributes("-alpha",0.35)
        ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
        cv=tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
        d={"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
        def dn(e): d["x1"],d["y1"]=e.x_root,e.y_root; d["r"]=cv.create_rectangle(e.x,e.y,e.x,e.y,outline="#89b4fa",width=4)
        def mv(e):
            if d["r"]: cv.coords(d["r"],d["x1"]-ov.winfo_rootx(),d["y1"]-ov.winfo_rooty(),e.x,e.y)
        def up(e):
            d["x2"],d["y2"]=e.x_root,e.y_root
            x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
            if x2-x1<8 or y2-y1<3: ov.destroy(); return
            global MNA_ROI; MNA_ROI=(x1,y1,x2,y2)
            save_hidden_config(loaded_pwd if (loaded_pwd) else "")
            ov.destroy()
            admin.after(300, lambda: refresh_preview(mna_roi_preview,mna_roi_lbl,MNA_ROI,MNA_100_REF,True))
        cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
        tk.Label(ov,text="💙 마나바 왼쪽→오른쪽 드래그",fg="#89b4fa",bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
        tk.Label(ov,text="ESC=취소",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
        ov.bind("<Escape>",lambda e:ov.destroy())

    def set_mna_100ref():
        global MNA_100_REF
        x1,y1,x2,y2=MNA_ROI
        if x1==0 and x2==0: return
        import mss as _mss; sct = _mss.MSS()
        img = sct.grab({"left": x1, "top": y1, "width": max(x2-x1,1), "height": max(y2-y1,1)})
        arr = np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
        blue = (arr[:,:,2]>50)&(arr[:,:,2]>arr[:,:,0]*1.1)&(arr[:,:,2]>arr[:,:,1]*1.1)
        MNA_100_REF = int(np.sum(blue))
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        messagebox.showinfo("100% 기준","[마나] 저장됨: "+str(MNA_100_REF)+"px")
        admin.after(300, lambda: refresh_preview(mna_roi_preview,mna_roi_lbl,MNA_ROI,MNA_100_REF,True))

    def set_party_100ref(pi):
        x1,y1,x2,y2=PARTY_ROIS[pi]
        if x1==0: return
        import mss as _mss; sct=_mss.MSS()
        img=sct.grab({"left":x1,"top":y1,"width":max(x2-x1,1),"height":max(y2-y1,1)})
        arr=np.array(img,dtype=np.uint8)[:,:,:3][:,:,::-1]
        PARTY_HP_100_REF[pi]=max(1, _hp_bar_band_cols(arr)[0])
        save_hidden_config(loaded_pwd if (loaded_pwd) else "")
        pv=entries.get(f"P{pi+1}_PREVIEW")
        if pv: refresh_preview(pv, None, PARTY_ROIS[pi], PARTY_HP_100_REF[pi])

    def _set_thr(i, v, l):
        PARTY_HP_THRESHOLDS[i] = v.get()
        l.configure(text=f"{v.get()}%")
        try: save_hidden_config(loaded_pwd)
        except: pass

    def open_party_roi_overlay(pi):
        ov = tk.Toplevel(admin); ov.attributes("-fullscreen",True); ov.attributes("-alpha",0.35)
        ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
        cv = tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
        d = {"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
        def dn(e): d["x1"],d["y1"]=e.x_root,e.y_root; d["r"]=cv.create_rectangle(e.x,e.y,e.x,e.y,outline="#10b981",width=4)
        def mv(e):
            if d["r"]: cv.coords(d["r"],d["x1"]-ov.winfo_rootx(),d["y1"]-ov.winfo_rooty(),e.x,e.y)
        def up(e):
            d["x2"],d["y2"]=e.x_root,e.y_root
            x1=min(d["x1"],d["x2"]); y1=min(d["y1"],d["y2"]); x2=max(d["x1"],d["x2"]); y2=max(d["y1"],d["y2"])
            if x2-x1<8 or y2-y1<3: ov.destroy(); return
            PARTY_ROIS[pi]=(x1,y1,x2,y2)
            PARTY_COORDS[pi]=[(x1+x2)//2,(y1+y2)//2]
            if f"P{pi+1}_BAR" in entries: entries[f"P{pi+1}_BAR"].set(1.0)
            if f"P{pi+1}_ROI_LBL" in entries:
                entries[f"P{pi+1}_ROI_LBL"].configure(text=f"({x1},{y1}) {x2-x1}x{y2-y1}")
            save_hidden_config(loaded_pwd if (loaded_pwd) else "")
            ov.destroy()
            pv = entries.get(f"P{pi+1}_PREVIEW")
            if pv:
                admin.after(300, lambda p=pi, w=pv: refresh_preview(w, None, PARTY_ROIS[p], PARTY_HP_100_REF[p]))
        cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
        tk.Label(ov,text=f"🟢 P{pi+1} HP바 드래그",fg="#10b981",bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
        tk.Label(ov,text="ESC=취소",fg="#6c7086",bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
        ov.bind("<Escape>",lambda e:ov.destroy())

    # --- 쫄법 피통 섹션 ---
    row_self_btns = ctk.CTkFrame(scrollable_frame, fg_color="transparent"); row_self_btns.pack(fill="x", pady=1)
    ctk.CTkButton(row_self_btns, text="🖱️ 쫄법 피통 셋팅", height=22, fg_color="#1f538d", hover_color="#14375e", font=("Malgun Gothic", 9, "bold"), command=open_self_hp_overlay).pack(side="left", padx=1)
    ctk.CTkButton(row_self_btns, text="💯 100% 기준", height=22, fg_color="#fbbf24", hover_color="#d97706", text_color="#000", font=("Malgun Gothic", 9, "bold"), command=set_self_100ref).pack(side="left", padx=1)
    self_roi_preview = tk.Label(scrollable_frame, bg="black"); self_roi_preview.pack(pady=1)
    self_roi_lbl = ctk.CTkLabel(scrollable_frame, text="", text_color="#f0f0f0", font=("Consolas", 9)); self_roi_lbl.pack(pady=(0, 2))
    ctk.CTkLabel(scrollable_frame, text="-"*70, text_color="#45475a", height=10).pack(pady=1)
    # --- 마나 엠통 섹션 ---
    row_mna_btns = ctk.CTkFrame(scrollable_frame, fg_color="transparent"); row_mna_btns.pack(fill="x", pady=1)
    ctk.CTkButton(row_mna_btns, text="💙 마나 엠통 셋팅", height=22, fg_color="#1e40af", hover_color="#2563eb", font=("Malgun Gothic", 9, "bold"), command=open_mna_roi_overlay).pack(side="left", padx=1)
    ctk.CTkButton(row_mna_btns, text="💯 100% 기준", height=22, fg_color="#fbbf24", hover_color="#d97706", text_color="#000", font=("Malgun Gothic", 9, "bold"), command=set_mna_100ref).pack(side="left", padx=1)
    mna_roi_preview = tk.Label(scrollable_frame, bg="black"); mna_roi_preview.pack(pady=1)
    mna_roi_lbl = ctk.CTkLabel(scrollable_frame, text="", text_color="#f0f0f0", font=("Consolas", 9)); mna_roi_lbl.pack(pady=(0, 2))
    ctk.CTkLabel(scrollable_frame, text="-"*70, text_color="#45475a", height=10).pack(pady=1)
    
    ctk.CTkLabel(scrollable_frame, text="👥 파티원 좌표 / ROI / 힐% (ROI 드래그로 설정)", text_color="#bac2de", font=("Malgun Gothic", 10, "bold"), height=15).pack(anchor="w", pady=(0, 2))

    party_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    party_frame.pack(fill="x", pady=1)

    def add_party_cell(parent, index, prefix, vx, vy):
        pi = index - 1
        cell = ctk.CTkFrame(parent, fg_color="#313244", corner_radius=6)
        # row 0 헤더: [체크박스] [P이름]  [ROI 좌표]
        hdr = ctk.CTkFrame(cell, fg_color="transparent"); hdr.grid(row=0, column=0, columnspan=3, pady=(4,2), sticky="ew")
        chk_var = ctk.BooleanVar(value=bool(party_mode_flags[pi]))
        def _on_chk(i=pi, v=chk_var):
            global party_mode_flags, saved_party_mode_flags
            party_mode_flags[i] = 1 if v.get() else 0
            saved_party_mode_flags = ",".join(str(f) for f in party_mode_flags)
            try: save_hidden_config(loaded_pwd)
            except: pass
        ctk.CTkCheckBox(hdr, text="", variable=chk_var, width=16, height=16,
                       checkbox_width=14, checkbox_height=14, border_width=1,
                       checkmark_color="#ffffff", fg_color="#800020", hover_color="#9e1a3a", command=_on_chk).pack(side="left", padx=(4,4))
        lbl_txt = f"P{index}(본인)" if index == 1 else (f"P{index}(격수)" if index == 2 else f"P{index}")
        ctk.CTkLabel(hdr, text=lbl_txt, text_color="#cba6f7", font=("Malgun Gothic", 9, "bold")).pack(side="left", padx=(0,4))
        r = PARTY_ROIS[pi]
        roi_info = f"({r[0]},{r[1]}) {r[2]-r[0]}x{r[3]-r[1]}" if r[0] != 0 else "ROI 미설정"
        roi_coord_lbl = ctk.CTkLabel(hdr, text=roi_info, text_color="#ffffff", font=("Consolas", 9))
        roi_coord_lbl.pack(side="left"); entries[f"{prefix}_ROI_LBL"] = roi_coord_lbl
        # row 1 roi_row
        roi_row = ctk.CTkFrame(cell, fg_color="transparent"); roi_row.grid(row=1, column=0, columnspan=3, pady=(0,4), sticky="ew")
        pv_frame = ctk.CTkFrame(cell, fg_color="transparent"); pv_frame.grid(row=2, column=0, columnspan=3, pady=(0,4), sticky="w")
        pv = tk.Label(pv_frame, bg="black"); pv.pack(side="left", padx=(4,4)); entries[f"{prefix}_PREVIEW"] = pv
        ctk.CTkButton(pv_frame, text="💯", width=22, height=22, fg_color="#fbbf24", hover_color="#d97706", text_color="#000", font=("Malgun Gothic", 8, "bold"),
                     command=lambda i=pi: set_party_100ref(i)).pack(side="left")
        roi_btn = ctk.CTkButton(roi_row, text="📍ROI", width=38, height=20, fg_color="#1f538d", hover_color="#14375e", font=("Malgun Gothic", 8, "bold"),
                                command=lambda i=pi: open_party_roi_overlay(i)); roi_btn.pack(side="left", padx=(4,2))
        hp_bar = ctk.CTkProgressBar(roi_row, width=50, height=10, fg_color="#45475a", progress_color="#10b981")
        hp_bar.set(0); hp_bar.pack(side="left", padx=1); entries[f"{prefix}_BAR"] = hp_bar
        hp_pct_lbl = ctk.CTkLabel(roi_row, text="--%", text_color="#6c7086", font=("Malgun Gothic", 8, "bold"), width=28)
        hp_pct_lbl.pack(side="left"); entries[f"{prefix}_PCT"] = hp_pct_lbl
        ctk.CTkLabel(roi_row, text="힐↓", text_color="#f38ba8", font=("Malgun Gothic", 8)).pack(side="left", padx=(3,1))
        var = tk.IntVar(value=PARTY_HP_THRESHOLDS[pi])
        sld = ctk.CTkSlider(roi_row, from_=10, to=90, number_of_steps=16, width=45, height=18, corner_radius=9, fg_color="#21262d", button_color="#10b981", button_hover_color="#34d399", progress_color="#f38ba8", variable=var)
        sld.pack(side="left", padx=1)
        thr_lbl = ctk.CTkLabel(roi_row, text=f"{var.get()}%", text_color="#f38ba8", font=("Malgun Gothic", 9, "bold"), width=24)
        thr_lbl.pack(side="left")
        var.trace_add("write", lambda *a, i=pi, v=var, l=thr_lbl: _set_thr(i, v, l))
        if r[0] != 0:
            admin.after(150, lambda p=pi, w=pv: refresh_preview(w, None, PARTY_ROIS[p], PARTY_HP_100_REF[p]))
        return cell

    for i in range(8): 
        row = i // 2; col = i % 2
        cell = add_party_cell(party_frame, i+1, f"P{i+1}", PARTY_COORDS[i][0], PARTY_COORDS[i][1])
        cell.grid(row=row, column=col, padx=2, pady=2)

    def auto_refresh():
        if not admin.winfo_exists(): return
        if SELF_HP_ROI[0] != 0: refresh_preview(self_roi_preview, self_roi_lbl, SELF_HP_ROI, SELF_HP_100_REF, strict=False)
        if MNA_ROI[0] != 0: refresh_preview(mna_roi_preview, mna_roi_lbl, MNA_ROI, MNA_100_REF, True)
        for pi in range(8):
            if PARTY_ROIS[pi][0] != 0:
                pv = entries.get(f"P{pi+1}_PREVIEW")
                if pv: refresh_preview(pv, None, PARTY_ROIS[pi], PARTY_HP_100_REF[pi])
        admin.after(1000, auto_refresh)
    auto_refresh()

    def save_and_close():
        key_to_save = loaded_pwd if (loaded_pwd and loaded_pwd != chr(34)+chr(34)) else ""
        save_hidden_config(key_to_save)
        messagebox.showinfo("저장 완료", "✨ 설정이 저장되었습니다!")
        admin.destroy()

    def on_closing():
        try: keyboard.unhook_key('f2')
        except: pass
        key_to_save = loaded_pwd if (loaded_pwd and loaded_pwd != chr(34)+chr(34)) else ""
        save_hidden_config(key_to_save)
        admin.destroy()

    admin.protocol("WM_DELETE_WINDOW", on_closing)
    ctk.CTkButton(admin, text="💾 실시간 저장 및 닫기", height=35, font=("Malgun Gothic", 12, "bold"), fg_color="#800020", hover_color="#9e1a3a", border_width=2, border_color="#4a0010", text_color="#ffffff", command=save_and_close).pack(side="bottom", fill="x", pady=10, padx=15)
    scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(5,0))
    update_admin_live()

def open_guide_panel():
    guide = ctk.CTkToplevel(root)
    guide.title("📖 뚱시스템 사용 가이드")
    w, h = 420, 520
    sw = guide.winfo_screenwidth(); sh = guide.winfo_screenheight()
    guide.geometry(f"{w}x{h}+{int((sw-w)/2)}+{int((sh-h)/2)}")
    guide.attributes("-topmost", True); guide.focus_force(); guide.grab_set()
    guide.configure(fg_color="#181825")
    sf = ctk.CTkScrollableFrame(guide, fg_color="#1e1e2e", corner_radius=8)
    sf.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(sf, text="⚠️ 본 프로그램 사용 시 책임은 사용자에게 있습니다.",
                 text_color="#f38ba8", font=("Malgun Gothic", 10, "bold")).pack(anchor="w", padx=8, pady=(4,0))
    ctk.CTkLabel(sf, text="감수하시고 사용하시고 6개월째 제것만 정지 없습니다.",
                 text_color="#a6adc8", font=("Malgun Gothic", 9)).pack(anchor="w", padx=8, pady=(0,0))
    ctk.CTkLabel(sf, text="항상 후원 감사합니다. ❤️",
                 text_color="#f9e2af", font=("Malgun Gothic", 9)).pack(anchor="w", padx=8, pady=(0,8))

    def add_t(txt): ctk.CTkLabel(sf, text=txt, text_color="#ffffff", font=("Malgun Gothic", 14, "bold")).pack(anchor="w", pady=(10, 5))
    def add_d(t1, t2):
        f = ctk.CTkFrame(sf, fg_color="transparent"); f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=t1, text_color="#ffffff", font=("Malgun Gothic", 11, "bold"), width=60, anchor="w").pack(side="left")
        ctk.CTkLabel(f, text=t2, text_color="#ffffff", font=("Malgun Gothic", 11, "bold"), justify="left").pack(side="left")
    def add_w(txt):
        ctk.CTkLabel(sf, text="• " + txt, text_color="#ffffff", font=("Malgun Gothic", 11, "bold"), justify="left", wraplength=350).pack(anchor="w", pady=2, padx=5)
    add_t("⌨️ 단축키 안내")
    add_d("[Insert]", "시작 / 종료 (토글 버튼)")
    add_d("[Home]", "클릭 (마우스 왼쪽 무한클릭, 따라다니기)")
    add_d("[PgUp]", "고정 (따라다니다 누르면 그 자리 멈춤)")
    add_d("[Delete]", "폼창 숨기기 / 다시 보이기")
    add_d("[ F4 ]", "주변 줍기 켜기 / 끄기 (토글)")
    ctk.CTkLabel(sf, text="-"*55, text_color="#45475a").pack(pady=5)
    add_t("🛡️ 스위치 및 설정")
    add_d("버프", "▶ 버프 펼침 → F1/F2/F3 단축창 선택 후 F5~F12 체크·초 설정")
    add_d("독 해독", "본인 독 걸리면 엔줄 자동 섭취 (두번째단축키 F9)")
    add_d("격수 해독", "격수 독 걸리면 큐어포이즌 자동 시전 (두번째단축키 F10)")
    add_d("파티 해독", "파티원 HP바 초록(독)이면 파티창 클릭 후 큐어포이즌 (F2→F10→F1, 격수해독과 동일)")
    add_d("파란물약", "두번째단축키 F8 · 엠통% 이하 시 10분마다 자동 복용")
    add_d("확률(%)", "0%: 물약만 / 100%: 힐만 / 그 외: 섞어서 확률 시전")
    add_d("자힐% 슬라이더", "본인 체력이 몇% 이하일 때 자동 힐")
    add_d("위기% 슬라이더", "위험한 피통 이하일 때 위험베르 자동 사용")
    add_d("격수% 슬라이더", "노파티 모드 UDP로 받은 격수 체력 기준")
    add_d("격수 모니터", "UDP로 받은 격수 HP를 폼 하단에 표시")
    ctk.CTkLabel(sf, text="-"*55, text_color="#45475a").pack(pady=5)
    add_t("🚨 주의사항 (필독)")
    add_w("파티 모드 시 쫄법사는 파티창이 활성화된 상태여야 합니다 (안 그러면 베르)")
    add_w("솔로(파티) 모드는 1:1 맨투맨, 무조건 따라다니기(Home) 켜야 정상 작동합니다")
    add_w("노파티 모드는 비비기만 됩니다 (제자리 힐 불가)")
    add_w("노파티 힐은 고정(PgUp) 상태에서만 제자리 힐이 동작합니다")
    add_w("제어판에서 파티원 HP바를 드래그로 설정 후 💯 100% 기준을 꼭 저장하세요")
    ctk.CTkLabel(sf, text="-"*55, text_color="#45475a").pack(pady=5)
    add_t("🕹️ 장치 (뚱USB / 뚱박스)")
    add_w("상단 [장치]에서 뚱USB(기존) 또는 뚱박스 중 선택합니다")
    add_w("뚱USB: 꽂으면 자동 인식, 설정 필요 없음 (기존 사용자는 그대로)")
    add_w("뚱박스: 박스 화면에 뜬 IP·포트·UUID를 입력칸에 넣고 [설정저장] 후 시작")
    add_w("뚱박스 처음 쓸 때 필요한 파일은 자동으로 받아집니다 (인터넷 연결 필요)")
    add_w("뚱박스 화면에 로고가 뜹니다 — 사냥 중엔 움직이고, 멈추면 박스 정보가 다시 보입니다")
    add_w("박스 정보(IP 등) 다시 보려면 멈춘 상태에서 마우스를 뺐다 끼우세요")
    ctk.CTkButton(guide, text="닫기", command=guide.destroy, fg_color="#313244", hover_color="#45475a", text_color="#ffffff", font=("Malgun Gothic", 12, "bold")).pack(pady=10)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

authenticated = False

if loaded_pwd:
    # 🔒 실시간 구글시트 검증 (마스터키 없음, HWID 강제)
    cs_result, cs_info, cs_start = check_google_sheet(loaded_pwd)
    if cs_result == "PASS":
        # 만료일 검사
        if cs_info == "0":
            # 0 = 즉시 만료
            ctypes.windll.user32.MessageBoxW(0, "사용 기간이 만료된 코드입니다.", "만료", 0x10)
            sys.exit()
        elif cs_info and cs_info != "":
            try:
                # 절대날짜 (예: 2026-07-20)
                expire_dt = datetime.strptime(cs_info, "%Y-%m-%d")
                if datetime.now() > expire_dt:
                    ctypes.windll.user32.MessageBoxW(0, "사용 기간이 만료된 코드입니다.", "만료", 0x10)
                    sys.exit()
            except:
                try:
                    # 일수 (예: 30 → 첫 사용 후 30일)
                    max_days = int(cs_info)
                    start_str = cs_start or datetime.now().strftime("%Y-%m-%d")
                    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
                    if (datetime.now() - start_dt).days >= max_days:
                        ctypes.windll.user32.MessageBoxW(0, "사용 기간이 만료된 코드입니다.", "만료", 0x10)
                        sys.exit()
                except: pass
        authenticated = True
    elif cs_result == "REGISTER":
        # HWID 자동 등록 시도
        if GAS_API_URL:
            try:
                reg_data = json.dumps({"code": loaded_pwd, "hwid": MY_HWID}).encode()
                reg_req = urllib.request.Request(GAS_API_URL, data=reg_data, headers={"Content-Type": "application/json"})
                reg_resp = json.loads(urllib.request.urlopen(reg_req, timeout=8).read())
                if reg_resp.get("result") == "OK":
                    authenticated = True
                else:
                    ctypes.windll.user32.MessageBoxW(0, "HWID 등록 실패. 관리자에게 문의하세요.", "등록 오류", 0x10)
                    sys.exit()
            except:
                ctypes.windll.user32.MessageBoxW(0, "인증 서버 연결 실패.", "네트워크 오류", 0x10)
                sys.exit()
        else:
            authenticated = True
    elif cs_result == "ALREADY_IN_USE":
        ctypes.windll.user32.MessageBoxW(0, "다른 PC에서 사용중인 코드입니다.", "HWID 불일치", 0x10)
        sys.exit()
    elif cs_result == "NOT_FOUND":
        if os.path.exists(AUTH_FILE):
            ctypes.windll.kernel32.SetFileAttributesW(AUTH_FILE, 128)
            try: os.remove(AUTH_FILE)
            except: pass
        authenticated = False
    elif cs_result == "ERROR":
        ctypes.windll.user32.MessageBoxW(0, "인증 서버 연결 실패. 인터넷을 확인하세요.", "네트워크 오류", 0x10)
        sys.exit()
    else:
        authenticated = False

# 첫 사용일 자동 저장
if authenticated and cs_info and cs_info != "0":
    try: int(cs_info)  # 숫자(일수)인 경우만 첫사용일 저장
    except: pass
    else:
        if not saved_expire_start or saved_expire_start == "":
            saved_expire_start = datetime.now().strftime("%Y-%m-%d")
            try: save_hidden_config(loaded_pwd if loaded_pwd else "")
            except: pass

else:
    auth_root = ctk.CTk()
    auth_root.title("뚱시스템 VIP 인증")
    sw = auth_root.winfo_screenwidth(); sh = auth_root.winfo_screenheight()
    aw, ah = 280, 280
    auth_root.geometry(f"{aw}x{ah}+{int((sw-aw)/2)}+{int((sh-520)/2)}") 
    auth_root.attributes("-topmost", True)
    auth_root.configure(fg_color='#1e1e2e')
    def check_login(event=None):
        global authenticated, SERIAL_PORT, loaded_pwd
        pwd = pw_entry.get().strip()
        user_com = com_entry.get().strip().upper()
        if not pwd: return
        if user_com: SERIAL_PORT = user_com
        server_result, server_info, server_start = check_google_sheet(pwd)
        if server_result == "PASS":
            global saved_expire_start, saved_expire_days
            if server_info == "0":
                err_lbl.configure(text="만료된 코드입니다")
                return
            elif server_info != "":
                saved_expire_start = server_start or datetime.now().strftime("%Y-%m-%d"); saved_expire_days = server_info
            else: saved_expire_start = ""; saved_expire_days = "0"
            save_hidden_config(pwd); loaded_pwd = pwd; authenticated = True
            auth_root.destroy()
        elif server_result == "REGISTER":
            global GAS_API_URL
            if GAS_API_URL:
                try:
                    reg_data = json.dumps({"code": pwd, "hwid": MY_HWID}).encode()
                    reg_req = urllib.request.Request(GAS_API_URL, data=reg_data, headers={"Content-Type": "application/json"})
                    reg_resp = json.loads(urllib.request.urlopen(reg_req, timeout=8).read())
                    if reg_resp.get("result") == "OK":
                        if server_info != "0": saved_expire_start = datetime.now().strftime("%Y-%m-%d"); saved_expire_days = server_info
                        else: saved_expire_start = ""; saved_expire_days = "0"
                        save_hidden_config(pwd); loaded_pwd = pwd; authenticated = True
                        auth_root.destroy()
                    else:
                        err_lbl.configure(text="이미 다른 PC에서 등록된 코드입니다")
                except:
                    err_lbl.configure(text="인증 서버 연결 실패")
            else:
                err_lbl.configure(text="API 설정이 필요합니다")
        elif server_result == "ALREADY_IN_USE":
            err_lbl.configure(text="다른 PC에서 사용 중인 코드입니다")
        elif server_result == "NOT_FOUND":
            err_lbl.configure(text="등록되지 않은 코드입니다")
        else:
            err_lbl.configure(text="인증에 실패했습니다")
    ctk.CTkLabel(auth_root, text="🔑 인증 코드를 입력하세요", text_color='#cba6f7', font=('Malgun Gothic', 13, 'bold')).pack(pady=(20, 5))
    pw_entry = ctk.CTkEntry(auth_root, show="●", font=('Malgun Gothic', 12), justify='center', fg_color='#313244', text_color='#cdd6f4', width=180, height=28)
    pw_entry.pack(pady=5); pw_entry.bind('<Return>', check_login)
    ctk.CTkLabel(auth_root, text="🔌 포트 번호", text_color='#a6adc8', font=('Malgun Gothic', 10)).pack(pady=(10, 2))
    com_entry = ctk.CTkEntry(auth_root, font=('Malgun Gothic', 11), justify='center', fg_color='#313244', text_color='#a6e3a1', width=120, height=28)
    com_entry.pack(pady=5); com_entry.insert(0, SERIAL_PORT)
    err_lbl = ctk.CTkLabel(auth_root, text="", text_color="#ef4444", font=("Malgun Gothic", 9))
    err_lbl.pack(pady=(0, 5))
    ctk.CTkButton(auth_root, text="시스템 잠금 해제", command=check_login, fg_color='#89b4fa', hover_color="#74c7ec", text_color='#1e1e2e', font=('Malgun Gothic', 11, 'bold'), width=180, height=30).pack(pady=15)
    auth_root.mainloop()

if not authenticated:
    sys.exit()

import mss as _mss
import threading as _threading

class MSSCamera:
    """스레드 안전 mss 캡처.
    - 스레드마다 별도 MSS 인스턴스(thread-local) → mss는 스레드 안전하지 않으므로 필수.
    - grab 일시 오류 시 마지막 정상 프레임 반환 → None/검은프레임 오작동 방지.
    - dxcam 미사용 → Desktop Duplication 네이티브 크래시 원천 제거."""
    def __init__(self):
        self._local = _threading.local()
        self._monitor = None
        self._last_frame = None
        self._flock = Lock()
        try:
            _s = _mss.MSS()
            self._monitor = _s.monitors[1]
            _s.close()
        except Exception:
            self._monitor = None
    def _get_sct(self):
        sct = getattr(self._local, "sct", None)
        if sct is None:
            sct = _mss.MSS()
            self._local.sct = sct
            if self._monitor is None:
                self._monitor = sct.monitors[1]
        return sct
    def start(self, **kw): pass
    def stop(self): pass
    def release(self):
        sct = getattr(self._local, "sct", None)
        if sct is not None:
            try: sct.close()
            except Exception: pass
            self._local.sct = None
    def get_latest_frame(self):
        try:
            sct = self._get_sct()
            img = sct.grab(self._monitor)
            arr = np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
            with self._flock:
                self._last_frame = arr
            return arr
        except Exception:
            with self._flock:
                return self._last_frame
    def grab_roi(self, roi):
        """ROI 좌표만 직접 캡처(전체화면 프레임을 잘라쓰지 않음) — 미리보기(refresh_preview)와
        완전히 동일한 방식. 모니터 오프셋 등으로 전체화면 프레임 슬라이싱이 실제 화면과
        어긋날 가능성을 원천적으로 없애기 위해, 절대좌표로 그 부분만 바로 캡처한다."""
        try:
            x1, y1, x2, y2 = roi
            sct = self._get_sct()
            img = sct.grab({"left": x1, "top": y1, "width": max(x2 - x1, 1), "height": max(y2 - y1, 1)})
            return np.array(img, dtype=np.uint8)[:, :, :3][:, :, ::-1]
        except Exception:
            return None

camera = MSSCamera()

def get_rgb(frame, x, y):
    try:
        p = frame[y, x]
        return int(p[0]), int(p[1]), int(p[2]) 
    except: return -1, -1, -1

def chk_color(f, coord, target_rgb, tol=25):
    if coord[0] == 0 and coord[1] == 0: return False
    r, g, b = get_rgb(f, coord[0], coord[1])
    if r == -1 or (r == 0 and g == 0 and b == 0): return False
    return abs(r - target_rgb[0]) <= tol and abs(g - target_rgb[1]) <= tol and abs(b - target_rgb[2]) <= tol

def _hp_bar_poisoned(red_cnt, green_cnt, total):
    """독(초록바) 판별 — HP% 계산과 분리."""
    return green_cnt > total * 0.05 or (green_cnt > red_cnt and green_cnt > total * 0.02)

def _hp_fill_masks(R, G, B):
    """빨강 HP / 초록(독) HP 채움 마스크.
    노란 선택테두리(R,G 둘 다 높음)·회색UI·어두운 빈칸은 R>G+30 / G>R+30 조건에서 모두 제외됨."""
    red = (R > 70) & (R > G + 30) & (R > B + 30)
    grn = (G > 70) & (G > R + 30) & (G > B + 30)   # 독(초록)바
    return red, grn

def _hp_bar_pixels(R, G, B):
    """호환용 — 빨강|초록(독) 채움 마스크."""
    red, grn = _hp_fill_masks(R, G, B)
    return red | grn

def _self_hp_fill_masks(R, G, B):
    """쫄법(자기) HP·위기베르 전용 채움 마스크 — 빨강뿐 아니라 위험경고색(주황·노랑)이나
    독(초록)으로 바뀌어도 전부 '채워짐'으로 인식한다.
    파티용 마스크(_hp_fill_masks)는 노란 선택테두리 오인식을 막기 위해 R>G+30(빨강 엄격)/
    G>R+30(초록 엄격)만 잡지만, 자기 피통 ROI는 그런 노란 테두리가 없는 단일 바이므로
    채도만 있으면(파랑이 주가 아니면) 색상 종류와 무관하게 채움으로 잡아도 안전함.

    실제 UI: 피가 빠지면 뒤에 흰색 배경이 드러나면서 빨간 채움이 줄어드는 방식.
    흰색은 채도가 없어서(R≈G≈B) 아래 sat 조건에서 이미 확실히 제외됨.
    (직전 버그: '가장 밝은 픽셀 대비 상대밝기'를 채도 필터링 *전* 전체 픽셀 기준으로
    계산해서, 채도 없는 흰 배경의 밝기(255)가 기준을 끌어올려버림 → 정작 진짜
    빨간 채움 픽셀 자체의 밝기가 그 기준(peak*0.6)에 못 미쳐 통째로 탈락하는
    새 버그가 생겼음. 그래서 peak는 반드시 '이미 채도 조건을 통과한 픽셀'
    중에서만 계산해야 함 — 흰 배경이 기준에 영향을 못 주도록)."""
    mx = np.maximum(np.maximum(R, G), B)
    mn = np.minimum(np.minimum(R, G), B)
    candidate = ((mx - mn) > 40) & (B < mx - 15)   # 채도 있고 파랑이 주가 아닌, 색상후보만
    peak = float(mx[candidate].max()) if candidate.any() else 0.0
    bright_ok = mx >= max(60.0, peak * 0.6)
    return bright_ok & candidate

def _hp_bar_band_cols(arr):
    """ROI 안에서 실제 HP바 '행'을 자동 탐지 → 그 바에서 채워진 '열' 수와 폭 반환.
    노란 선택테두리·초상화·초록 장식테두리는 자동으로 무시된다.
    반환: (채움열수, 폭, 바있음여부)."""
    if arr.size == 0:
        return 0, 1, False
    R = arr[:, :, 0].astype(int)
    G = arr[:, :, 1].astype(int)
    B = arr[:, :, 2].astype(int)
    red, grn = _hp_fill_masks(R, G, B)
    h, w = red.shape
    start_window = max(3, w // 8)   # 진짜 HP바는 ROI 좌측에서 시작
    gap_tol = max(2, w // 20)       # 연속 판정 시 허용하는 작은 틈

    def _measure(mask, floor):
        """바 행 자동탐지 후 '세로로 꽉 찬 + 좌측에서 시작하는 연속 막대' 폭 측정.
        진짜 HP바 = 얇은 가로 사각형(밴드 높이의 대부분이 같은 색으로 채워짐).
        게임 배경(흩어진 빨강)·우측 시작 잡픽셀은 세로가 안 차거나 좌측시작이 아니라 걸러짐."""
        rows = mask.sum(axis=1)
        if int(rows.max()) < 2:
            return 0, False
        peak = int(rows.max()); py = int(np.argmax(rows))
        lo = py; hi = py
        while lo - 1 >= 0 and rows[lo - 1] >= peak * 0.4:
            lo -= 1
        while hi + 1 < h and rows[hi + 1] >= peak * 0.4:
            hi += 1
        sub = mask[lo:hi + 1]
        bh = sub.shape[0]
        need = max(2, math.ceil(bh * 0.6))   # 열이 밴드 높이의 60% 이상 채워야 '진짜 바 열'
        solid = sub.sum(axis=0) >= need
        idx = np.nonzero(solid)[0]
        if idx.size == 0:
            return 0, False
        first = int(idx[0])
        if first > start_window:              # 좌측 시작 아님 → 게임배경/잡픽셀 → 바 아님
            return 0, False
        run_end = first; gap = 0
        for c in range(first, w):
            if solid[c]:
                run_end = c; gap = 0
            else:
                gap += 1
                if gap > gap_tol:
                    break
        if (run_end - first + 1) < floor:     # 연속 막대 최소 길이 미달 → 바 아님
            return 0, False
        return run_end - first + 1, True

    red_cols, red_ok = _measure(red, max(3, w // 25))   # 빨강 HP (저피통 5%도 통과)
    if red_ok:
        return red_cols, w, True
    grn_cols, grn_ok = _measure(grn, max(8, w // 5))    # 독(초록)바는 넓게 채워질 때만
    if grn_ok:
        return grn_cols, w, True
    return 0, w, False        # 빈칸·사망·게임배경(바 없음)

def _hp_filled_cols(bar_px):
    """호환용 — 채워진 '열' 수(가로)."""
    if bar_px.size == 0:
        return 0
    return int(bar_px.any(axis=0).sum())

def _hp_bar_fill_span(bar_px):
    """호환용 — 채워진 열 수."""
    return _hp_filled_cols(bar_px)

def _hp_bar_lenient_cols(arr):
    """관대한 채움 폭 측정 — 쫄법(자기) HP·위기베르처럼 항상 바가 존재하는 단일 바용.
    피격 이펙트·데미지 텍스트 등으로 한 프레임 구조판정(세로꽉참/좌측시작)이 실패해도
    즉시 0%로 잘못 떨어지지 않도록, 색이 조금이라도 있으면 읽어낸다.
    단, '첫색~끝색 사이 거리(span)'가 아니라 '좌측부터 끊기지 않는 연속 열'만 센다 —
    span 방식은 우측 끝 UI잔상 1픽셀만 있어도 거의 100%로 뻥튀기되어
    실제로는 피가 20% 밑인데도 위기베르가 전혀 발동 안 하는 치명적 버그가 있었음."""
    R = arr[:, :, 0].astype(int); G = arr[:, :, 1].astype(int); B = arr[:, :, 2].astype(int)
    red, grn = _hp_fill_masks(R, G, B)
    h, w = red.shape
    mask = red if int(red.sum()) >= int(grn.sum()) else grn
    if int(mask.sum()) == 0:
        return 0, w
    rows = mask.sum(axis=1)
    peak = int(rows.max()); py = int(np.argmax(rows))
    lo = py; hi = py
    while lo - 1 >= 0 and rows[lo - 1] >= max(1, peak * 0.3):
        lo -= 1
    while hi + 1 < h and rows[hi + 1] >= max(1, peak * 0.3):
        hi += 1
    col = mask[lo:hi + 1].any(axis=0)
    start_window = max(3, w // 8)   # 바 시작 전 약간의 여백(테두리 등) 허용
    gap_tol = max(2, w // 20)       # 연속 판정 중 허용하는 작은 틈
    idx = np.nonzero(col)[0]
    if idx.size == 0 or int(idx[0]) > start_window:
        return 0, w                 # 좌측에 색이 없음 → 실제로 다 빠졌거나 바 아님
    run_end = int(idx[0]); gap = 0
    for c in range(int(idx[0]), w):
        if col[c]:
            run_end = c; gap = 0
        else:
            gap += 1
            if gap > gap_tol:
                break                # 큰 틈 이후의 우측 잔상/장식은 무시 (span 뻥튀기 방지)
    return run_end - int(idx[0]) + 1, w

def _self_hp_fill_cols(arr):
    """쫄법(자기) HP·위기베르 전용 — 파티 로직과 완전 분리, 구조판정(세로꽉참)도 안 하고
    '행 자동탐지'도 하지 않는다(예전 초기 버전처럼 최대한 단순하게).
    행밴드 자동탐지는 잘못된 행(피격플래시·잡노이즈 행 등)을 고르면 계산 전체가
    틀어지는 위험한 구조라 제거함 — ROI 전체 높이에서 그냥 '열별로 색이 있는지'만 보고,
    왼쪽부터 끊기지 않는 연속 열만 센다. 중앙 숫자표시가 안티앨리어싱으로 살짝 붉게
    잡혀도, 실제 채움이 적을 땐 숫자와 진짜 채움 사이에 틈이 생기므로 그 너머는 안 셈."""
    if arr.size == 0:
        return 0, 1
    R = arr[:, :, 0].astype(int); G = arr[:, :, 1].astype(int); B = arr[:, :, 2].astype(int)
    mask = _self_hp_fill_masks(R, G, B)
    h, w = mask.shape
    col = mask.any(axis=0)
    gap_tol = 2   # 진짜 이어진 바만 인정 — 크게 두면 중앙 숫자와의 틈을 뛰어넘어
                  # 이어붙여서 피가 얼마나 빠지든 숫자 위치까지의 값으로 고정되어버림.
                  # 안티앨리어싱 정도의 아주 작은 틈만 허용.
    idx = np.nonzero(col)[0]
    if idx.size == 0:
        return 0, w
    # 좌측 시작을 강제하지 않음 — 피격 플래시가 바 왼쪽 일부를 잠깐 가려도
    # (그래서 색이 처음 발견되는 위치가 뒤로 밀려도) 0%로 잘못 떨어지지 않게,
    # '색이 처음 발견된 지점'부터 끊기지 않는 연속 구간의 길이만 잰다.
    # 중앙 숫자표시처럼 진짜 채움과 떨어진 덩어리는 그 사이 큰 틈에서 자동으로 끊긴다.
    run_end = int(idx[0]); gap = 0
    for c in range(int(idx[0]), w):
        if col[c]:
            run_end = c; gap = 0
        else:
            gap += 1
            if gap > gap_tol:
                break                # 큰 틈 이후(중앙 숫자 등 별개 덩어리)는 무시
    return run_end - int(idx[0]) + 1, w

def _self_hp_pct_from_arr(arr, ref100=None):
    if arr.size == 0:
        return 100.0
    cols, w = _self_hp_fill_cols(arr)
    denom = ref100 if (ref100 and 0 < ref100 <= w) else w
    return min(100.0, round(cols / max(denom, 1) * 100, 1))

def self_hp_pct(frame, roi, ref100=None):
    """쫄법(자기) HP% — 위기베르·자힐 전용, 파티 판정과 무관."""
    x1, y1, x2, y2 = roi
    if x1 == 0 and x2 == 0:
        return 100.0
    try:
        return _self_hp_pct_from_arr(frame[y1:y2, x1:x2], ref100)
    except Exception:
        return 100.0

_last_selfhp_debug_pct = 100.0
_last_selfhp_debug_time = 0.0

def _debug_dump_self_hp(arr, roi, ref100, pct, prev_pct):
    """퍼센트가 순간적으로 크게 뚝 떨어질 때, 그 순간의 실제 ROI 픽셀 판정과정을
    화면 로그(log_event)에 바로 보이는 요약 문자열로 만들어 돌려준다 — 배포판이라
    파일을 못 꺼내는 다른 컴퓨터에서도, 화면 캡처만으로 원인 확인이 가능하게 함.
    arr는 이미 ROI만큼 잘라진(cropped) 이미지. 실패해도 프로그램에 영향 없음.
    (같은 컴퓨터에서 직접 확인 가능한 사람을 위해 _selfhp_debug 폴더에 PNG도 같이 남김)"""
    try:
        if arr is None or arr.size == 0:
            return None
        R = arr[:, :, 0].astype(int); G = arr[:, :, 1].astype(int); B = arr[:, :, 2].astype(int)
        mask = _self_hp_fill_masks(R, G, B)
        col = mask.any(axis=0)
        cols, w = _self_hp_fill_cols(arr)
        idx = np.nonzero(col)[0]
        start_c = int(idx[0]) if idx.size else -1
        end_c = start_c + cols - 1 if start_c >= 0 else -1
        rgb_start = tuple(int(v) for v in arr[arr.shape[0]//2, start_c]) if start_c >= 0 else (0,0,0)
        rgb_end = tuple(int(v) for v in arr[arr.shape[0]//2, min(end_c, w-1)]) if end_c >= 0 else (0,0,0)
        rgb_after = tuple(int(v) for v in arr[arr.shape[0]//2, min(end_c+1, w-1)]) if end_c >= 0 else (0,0,0)
        buckets = 30
        bar = "".join("#" if col[int(i*w/buckets):int((i+1)*w/buckets) or 1].any() else "." for i in range(buckets))
        summary = f"열{cols}/{w} 시작@{start_c}RGB{rgb_start} 끝@{end_c}RGB{rgb_end} 끝다음RGB{rgb_after} [{bar}]"
        try:
            os.makedirs("_selfhp_debug", exist_ok=True)
            ts = time.strftime("%H%M%S")
            base = os.path.join("_selfhp_debug", f"drop_{ts}_{prev_pct:.0f}to{pct:.0f}")
            Image.fromarray(arr).resize((arr.shape[1]*4, arr.shape[0]*4), Image.NEAREST).save(base + ".png")
            with open(base + ".txt", "w", encoding="utf-8") as f:
                f.write(f"roi={roi} ref100={ref100} prev_pct={prev_pct} pct={pct}\n{summary}\n")
        except Exception:
            pass
        return summary
    except Exception:
        return None

def bar_fill_pct_from_rgb(arr, ref100=None, strict=False):
    """HP바 채움% (파티 전용) — 바 행 자동탐지 후 채움 열 수 / 100%보정(열 수).
    노란 선택테두리·초상화·회색UI 자동 무시.
    strict=True(파티): 빈칸/사망 판정 시 0%. 이미 party_slot_active로 거른 뒤 호출되므로 안전."""
    if arr.size == 0:
        return 100.0
    cols, w, is_bar = _hp_bar_band_cols(arr)
    if is_bar:
        denom = ref100 if (ref100 and 0 < ref100 <= w) else w
        return min(100.0, round(cols / max(denom, 1) * 100, 1))
    if strict:
        return 0.0
    lcols, lw = _hp_bar_lenient_cols(arr)
    denom = ref100 if (ref100 and 0 < ref100 <= lw) else lw
    return min(100.0, round(lcols / max(denom, 1) * 100, 1))

def bar_fill_pct(frame, roi, ref100=None, strict=False):
    """HP바 채움% — ROI 가로 채움 span, 100% 보정 연동."""
    x1, y1, x2, y2 = roi
    if x1 == 0 and x2 == 0:
        return 100.0
    try:
        r = frame[y1:y2, x1:x2]
        return bar_fill_pct_from_rgb(r, ref100, strict=strict)
    except Exception:
        return 100.0

def roi_hp_pct(frame, roi, ref100=None):
    """쫄법(자기) HP% — 전체화면 프레임을 잘라쓰지 않고, 미리보기와 동일하게
    ROI 부분만 직접 캡처해서 계산(모니터 오프셋 등으로 전체화면 슬라이싱이
    실제 화면과 어긋날 가능성 제거). 직접캡처 실패시에만 기존 방식으로 대체."""
    if roi[0] == 0 and roi[2] == 0:
        return 100.0
    arr = camera.grab_roi(roi) if camera else None
    if arr is not None:
        return _self_hp_pct_from_arr(arr, ref100)
    return self_hp_pct(frame, roi, ref100)

def roi_mna_pct(frame, roi, ref100=None):
    x1,y1,x2,y2 = roi
    if x1==0 and x2==0: return 100.0
    try:
        r = frame[y1:y2,x1:x2]
        if r.size==0: return 100.0
        R,G,B = r[:,:,0].astype(int),r[:,:,1].astype(int),r[:,:,2].astype(int)
        blue = (B>50)&(B>R*1.1)&(B>G*1.1)
        raw = int(np.sum(blue))
        if ref100 and ref100>0: return min(100.0, round(raw/ref100*100,1))
        return min(100.0, round(raw/max(r.shape[0]*r.shape[1],1)*100,1))
    except: return 100.0

def is_gray_bar(frame, roi):
    if roi[0]==0 and roi[2]==0: return False
    x1,y1,x2,y2 = roi
    try:
        r = frame[y1:y2,x1:x2]
        if r.size==0: return False
        R,G,B = r[:,:,0].astype(int),r[:,:,1].astype(int),r[:,:,2].astype(int)
        gray = (abs(R-G)<35)&(abs(G-B)<35)&(abs(R-B)<35)&(R>20)&(R<170)
        red  = (R>80)&(R>G*1.2)&(R>B*1.2)
        gray_cnt = int(np.sum(gray))
        red_cnt = int(np.sum(red))
        total = r.shape[0]*r.shape[1]
        if gray_cnt > total*0.15 and red_cnt < total*0.03: return True
        avgR, avgG, avgB = float(np.mean(R)), float(np.mean(G)), float(np.mean(B))
        return abs(avgR-avgG)<25 and abs(avgG-avgB)<25 and abs(avgR-avgB)<25 and avgR>50 and avgR<180
    except: return False

def is_green_bar(frame, roi):
    if roi[0]==0 and roi[2]==0: return False
    x1,y1,x2,y2 = roi
    try:
        r = frame[y1:y2,x1:x2]
        if r.size==0: return False
        R,G,B = r[:,:,0].astype(int),r[:,:,1].astype(int),r[:,:,2].astype(int)
        green = (G>15)&(G>R*1.03)&(G>B*1.03)
        red   = (R>80)&(R>G*1.2)&(R>B*1.2)
        green_cnt = int(np.sum(green))
        red_cnt = int(np.sum(red))
        total = r.shape[0]*r.shape[1]
        if green_cnt > total*0.02 and red_cnt < total*0.03: return True
        avgR, avgG = float(np.mean(R)), float(np.mean(G))
        return avgG > avgR*1.05 and avgR < 120
    except: return False

def party_slot_active(frame, roi):
    """파티 슬롯에 HP바 존재 여부 — 빈칸·사망(바 없음/회색) 힐 차단."""
    x1, y1, x2, y2 = roi
    if x1 == 0 and x2 == 0:
        return False
    try:
        r = frame[y1:y2, x1:x2]
        return party_slot_active_rgb(r)
    except Exception:
        return False

def party_slot_active_rgb(arr):
    """슬롯에 실제 HP바(빨강 또는 넓은 독초록)가 있으면 True.
    빈칸·사망(바 없음)·노란 선택테두리만 있는 슬롯은 False → 힐 차단.
    독(초록)바는 인식됨 — 색 무관."""
    if arr.size == 0:
        return False
    _, _, is_bar = _hp_bar_band_cols(arr)
    return is_bar

def scan_party_hp(frame, pi):
    roi = PARTY_ROIS[pi]
    if roi[0] == 0 and roi[2] == 0:
        return None
    if not party_slot_active(frame, roi):
        return None
    return bar_fill_pct(frame, roi, PARTY_HP_100_REF[pi], strict=True)

def load_buff_templates():
    global buff_templates, buff_template_hu
    buff_names = {"bless": "buff_bless.png", "shield": "buff_shield.png", "blue": "buff_blue.png", "f10": "buff_f10.png", "f11": "buff_f11.png"}
    for key, fname in buff_names.items():
        if os.path.exists(fname):
            try:
                tpl = cv2.imread(fname, cv2.IMREAD_COLOR)
                if tpl is not None:
                    tpl_rgb = cv2.cvtColor(tpl, cv2.COLOR_BGR2RGB); buff_templates[key] = tpl_rgb
                    gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
                    moments = cv2.moments(gray); hu = cv2.HuMoments(moments)
                    buff_template_hu[key] = np.array([float(h[0]) for h in hu])
            except: pass

def human_delay(min_val, max_val):
    mean = (min_val + max_val) / 2; std_dev = (max_val - min_val) / 6 
    return max(min_val, min(max_val, random.gauss(mean, std_dev)))

def _clamp_to_screen(x, y, margin=4):
    """이동 목표를 (가상)화면 안으로 제한 + 좌측하단 시작 핫코너 회피.
    상대이동 오버슈트/경계 clamp로 커서가 코너(0,maxY=시작버튼)로 튀는 것 방지."""
    try:
        gm = ctypes.windll.user32.GetSystemMetrics
        vx, vy = gm(76), gm(77)          # 가상데스크톱 좌상단(멀티모니터 대응)
        vw, vh = gm(78), gm(79)          # 가상데스크톱 크기
        x = max(vx + margin, min(vx + vw - 1 - margin, int(x)))
        y = max(vy + margin, min(vy + vh - 1 - margin, int(y)))
    except Exception:
        pass
    return x, y

def human_mouse_move(tx, ty):
    global ser
    if not ser or not ser.is_open: return
    pt = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    cx, cy = pt.x, pt.y
    tx += random.randint(-2, 2); ty += random.randint(-2, 2)
    tx, ty = _clamp_to_screen(tx, ty)    # 화면 밖/핫코너 진입 차단 (목표·복귀 좌표 모두 경유)
    steps = random.randint(20, 30) 
    _km = (hw_var.get() in ("뚱박스", "KMBox")) if ('hw_var' in globals() and hw_var) else (HW_MODE in ("뚱박스", "KMBox"))
    # KMBox: 하드웨어가 ms 동안 직선을 부드럽게 보간(1패킷) → 네트워크 뚝뚝거림 제거, 아두이노 느낌.
    if _km and hasattr(ser, "move_smooth"):
        total_dx, total_dy = tx - cx, ty - cy
        dist = (total_dx * total_dx + total_dy * total_dy) ** 0.5
        ms = int(max(60, min(180, dist * 0.7)) * random.uniform(0.85, 1.15))
        if ser.move_smooth(total_dx, total_dy, ms):
            return
        # move_auto 미지원 pyd → 아래 기존 스텝방식으로 폴백
    px, py = cx, cy   # KMBox용 계산상 위치 추적 (박스 1:1 → 네트워크 지연 영향 제거)
    for i in range(1, steps + 1):
        t = i / steps; sc = (1 - float(math.cos(t * math.pi))) / 2 
        nx = int(cx + (tx - cx) * sc); ny = int(cy + (ty - cy) * sc)
        if _km:
            dx, dy = nx - px, ny - py; px, py = nx, ny        # KMBox: 수학추적
        else:
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)); dx, dy = nx - pt.x, ny - pt.y   # 아두이노: 원본 방식
        while abs(dx) > 100 or abs(dy) > 100:
            sx, sy = max(-100, min(100, dx)), max(-100, min(100, dy))
            try: ser.write(f"<{sx},{sy}>".encode())
            except: break
            time.sleep(human_delay(0.002, 0.004)); dx -= sx; dy -= sy
        if dx != 0 or dy != 0:
            try: ser.write(f"<{dx},{dy}>".encode())
            except: break
            time.sleep(human_delay(0.002, 0.004))

def execute_keys(keys, end_delay=0.5, skip_follow_toggle=False):
    global ser, running
    if not running: return
    if not ser or not getattr(ser, "is_open", False): return
    time.sleep(0.02)
    was_auto = chk_follow.get() if chk_follow else False
    if was_auto:
        try: ser.write(b'T'); time.sleep(0.06)
        except: return
    try:
        for k in keys:
            if not running: break
            ser.write(k.encode()); time.sleep(random.uniform(0.04, 0.15))
        if running: time.sleep(random.uniform(max(0.15, end_delay*0.7), max(0.5, end_delay*1.8)))
    finally:
        if not ser or not getattr(ser, "is_open", False): return
        if was_auto:
            try: ser.write(b'T'); time.sleep(0.04)
            except: pass

def fix_mode_keys(keys, delay=0.5):
    if not ser or not getattr(ser, "is_open", False): return
    if chk_fix and chk_fix.get():
        try: ser.write(b'U'); time.sleep(0.02)
        except: return
    execute_keys(keys, delay)
    if not ser or not getattr(ser, "is_open", False): return
    if chk_fix and chk_fix.get():
        try: ser.write(b'H'); time.sleep(0.02)
        except: pass

PATCH_UPDATED_AT = "2026-07-16 15:11"
LATEST_PATCH = [
    "🚨 쫄법 HP 상대밝기 계산버그 수정 — 흰 배경(채도없음)이 채도필터 적용 전에 기준밝기(peak)를 끌어올려서, 정작 진짜 빨간 채움이 그 기준에 못미쳐 통째로 탈락하던 문제. peak는 이미 채도조건 통과한 픽셀 중에서만 계산하도록 수정",
    "🚨 쫄법 HP 근본원인 수정 — 빈 피통(트랙)이 어두운 빨강/자주색이면 채움으로 같이 잡혀서 항상 100%로 고정되던 치명적 버그, 상대밝기 비교로 진짜 채움만 인식하도록 수정 (실전투 중 위기베르 전혀 반응 안 하던 근본원인)",
    "🩻 HP급락 진단정보를 화면 로그에 직접 표시 — 배포판/다른 컴퓨터에서도 파일없이 화면 캡처만으로 원인 확인 가능하게 변경",
    "🩻 쫄법 HP·위기베르 — 전체화면 캡처를 잘라쓰지 않고 ROI만 직접 캡처하도록 변경(미리보기와 100% 동일 경로) + HP급락시 실제픽셀 자동저장 진단기능 추가",
    "🚨 위험베르 연속2프레임 확인(디바운스) 제거 — 전투이펙트로 매프레임 흔들리면 연속확인이 오히려 실발동을 막던 치명적 문제, 즉시발동으로 복귀",
    "🔧 쫄법 HP% 행(row) 자동탐지 제거 — 잘못된 행을 고르면 전체가 틀어지는 위험요소였음, 예전 초기버전처럼 단순하게 복귀",
    "🛡️ 위험베르 오발동 방지 — 캡처 한프레임 순간오독 걸러내는 연속2프레임 확인 로직 추가",
    "🎨 쫄법 HP% 위험경고색(주황·노랑 등)으로 바뀌어도 채움 인식 — 색상 전환시 %가 훅 떨어지던 문제 대응",
    "🚨 쫄법 HP% 40% 밑으로 안 내려가던 바닥값 버그 수정 — 틈허용을 폭비례에서 고정 2px로 축소(숫자와 이어붙는 것 차단)",
    "🚨 쫄법 HP% 피격시 90%대에서도 0%로 오인식하던 버그 수정 — 좌측시작 강제 조건 제거(피격플래시 대응)",
    "🚨 쫄법 HP% 저피통일수록 실제보다 훨씬 높게 뻥튀기되던 문제 수정 — 바 중앙 숫자표시 오염 차단(좌측 연속구간만 인정)",
    "🎯 쫄법 HP% 정밀도 개선 — 바가 있는 행만 자동으로 좁혀서 셈 (ROI 여유분에 걸린 숫자·장식 오염 감소)",
    "🔧 쫄법 HP·위기베르 완전 독립화 — 파티 판정 로직과 100% 분리, 피 닳으면 그만큼만 단순·정확하게 반영",
    "🚨 위기베르 20%까지 피 빠져도 미발동 치명적 버그 수정 — 관대계산이 우측 잔상픽셀로 %를 뻥튀기하던 문제",
    "🖥️ 제어판 쫄법 피통 미리보기 — 피 깎이면 '없음(사망)' 오표시 수정 (실제 힐판정과 동일 계산식으로 통일)",
    "🛡️ 쫄법 HP·위기베르 한대맞고 오발동 수정 — 파티용 엄격판정과 분리, 관대한 계산으로 복귀",
    "🚫 빈 파티칸(게임배경만 있는 슬롯) 힐 차단 강화 — 세로로 꽉 찬 좌측시작 막대만 HP바로 인정",
    "🖱️ 마우스 좌측하단(시작버튼) 튐 방지 — 이동 좌표 화면경계 clamp 적용",
    "🛡️ 캡처 백엔드 mss 전용 전환 — dxcam 네이티브 크래시(전체화면 전환 등) 제거",
    "🎯 파티 HP 바행 자동탐지 — 선택 시 노란 테두리로 100% 오독되던 문제 해결",
    "🎯 HP 감지 색무관 재설계 — 밝기+채도로 채움 판정 (독=초록도 정상%, 0% 오독 해결)",
    "🚫 빈칸·사망만 힐 차단 — 채움 0일 때만 '없음' (독바를 사망으로 오인하던 버그 수정)",
    "🎯 파티 HP% 보정 수정 — 100%ref=채움컬럼 수 연동, ROI 테두리 오독(50%→93%) 차단",
    "👁 제어판 미리보기 = 실제 힐 판정 동일 계산식",
    "🩹 HP% 색상무관 — 빨강/초록(독) 모두 ROI 가로폭%로 계산 (위기·상위힐·익힐 오발동 차단)",
    "🟢 독·힐 분리 — 독은 해독용, 노파티 격수힐은 독 무관 HP% 임계값만 (상위힐 오발동 차단)",
    "🩹 격수 독 시 상위힐 오발동 수정 — 초록바는 가로폭%로 계산 (빨강 100% ref 오차 제거)",
    "⏱️ 버프 간격 랜덤화 — 1200초 고정 아님, 설정값 ±14% 흔들림 (사람처럼)",
    "🎯 노파티 격수 — 독(초록바) UDP HP% 정상 인식 + 독 걸려도 힐 우선",
    "✨ 버프 그리드 — F1/F2/F3 단축창 × F5~F12 체크 (뚱헌터 방식), F10/F11/2-F5 등 삭제",
    "▶ 접이식 UI — 옵션/버프/힐 섹션 펼침·접기 (폼 커짐 방지)",
    "💚 파티 해독 — 파티창 초록바 클릭 후 큐어포이즌 (F2→F10→F1)",
    "📅 상단 [업데이트] 날짜·시간으로 패치 반영 여부 확인 (이 줄 보이면 최신)",
    "👁 제어판 쫄법 피통/엠통 미리보기 글자 — 흰색·크게 (가독성)",
    "🖼️ 파티 ROI 미리보기 — 제어판 다시 열어도 유지·1초 자동 갱신",
    "🟢 독(초록 HP바)에서도 힐·위험베르 정상 — HP% 빨강/초록 자동 판별",
    "🩹 독 걸려도 HP% 기준으로 자힐·파티힐 동작 (해독과 분리)",
    "🔄 파티힐 원본 방식으로 복구 — 키 다섯개를 끊지 않고 한번에 눌러서 힐 지연 없앰",
    "🔄 키입력 내부 대기시간 원래대로 복구",
    "🔄 전체 감지 간격 0.25초로 원복",
    "✨ 이름이 '뚱힐러'로 바뀌었어요 — 힐 전용 시스템",
    "🖼️ 뚱박스 화면 로고를 뚱힐러 로고로 새단장",
    "🖱️ 뚱박스 마우스 이동 부드럽게 — 힐하러 갈 때 뚝뚝 끊겨 움직이던 것 없애고 자연스럽게 미끄러지듯 이동",
    "🎮 장치 선택 추가 — 상단에서 뚱USB(기존)와 뚱박스 중 골라 사용",
    "📡 뚱박스 지원 — 박스 화면의 IP·포트·UUID만 입력하면 바로 연결",
    "📌 사용법: 상단 [장치]에서 뚱박스 선택 → IP·포트·UUID 입력 → 설정저장 → 시작",
    "🖼️ 뚱박스 화면에 로고 표시 — 사냥 중엔 움직이는 로고, 멈추면 박스 정보 확인",
    "⬇️ 뚱박스 처음 연결 시 필요한 파일 자동 설치 (안 보이게 숨김)",
    "🛡️ 뚱박스 미연결 시 시작(Insert)해도 크래시 안 남 — 연결실패 메시지만 표시",
    "💾 장치·접속정보 설정저장하면 다음부터 자동 기억",
    "🔌 기존 뚱USB 사용자는 그대로 — 설정 안 바꿔도 예전과 똑같이 작동",
]
PAST_PATCHES = [
    "0703 - 화면캡처 GPU가속 복원 · 상위힐(F7) 추가 · 자동클릭 중 힐/물약 즉시동작 · 독 걸리면 위기귀환 방지 · 연결 자동인식 개선",
    "0627 - 자힐/해독 타이밍 랜덤화 · 고정상태 해독 · 석화시 위험베르 방지 · 마나부족시 자힐중단 · 인증재검사 강화",
    "0626 - 배치파일 개선 (파이썬·패키지 한방 설치) · 쫄법사/격수 배치파일 이름 변경",
    "0619 - 독·석화 감지 추가 · UI 타이머 개선 · 독해독 우선순위",
    "0618 - 격수 컴퓨터에서 쫄법사 키보드 직접 제어 · 단축키 매크로 · 격수원격제어 통합 · 창 디자인 개선",
    "0618 - 시작·따라가기·고정·줍기 토글을 격수 컴퓨터 버튼으로 조종 · 제어판 파티원 정렬 · 격수 체력 감지창 2줄 배치",
    "0617 - 피통 설정 오류 수정 · 격수감시 아이피 유지 · 마우스 속도 느리게 조정",
    "0616 - 파티원별 피통영역 드래그 설정 · 체력 퍼센트 자동감지 · 개별 힐 기준 조절",
    "0615 - 메인창과 제어판 체크박스 분리 · 파티 상태에서 선택된 파티원만 힐",
    "0612 - 버프 감지 정밀 판정 · 고정 풀 때 클릭 자동 복원 · 단축키 반응 2배 향상",
]

def open_patch_notes_panel():
    patch = ctk.CTkToplevel(root)
    patch.title("패치노트")
    w, h = 460, 480; sw = patch.winfo_screenwidth(); sh = patch.winfo_screenheight()
    patch.geometry(f"{w}x{h}+{int((sw-w)/2)}+{int((sh-h)/2)}")
    patch.attributes("-topmost", True); patch.focus_force(); patch.grab_set()
    patch.configure(fg_color="#181825")

    ctk.CTkLabel(patch, text="최신 업데이트 (%s)" % PATCH_UPDATED_AT,
                 text_color="#f9e2af", font=("Malgun Gothic", 13, "bold")).pack(pady=(12, 6))

    # 공지
    ctk.CTkLabel(patch, text="⚠️ 본 프로그램 사용 시 책임은 사용자에게 있습니다.",
                 text_color="#f38ba8", font=("Malgun Gothic", 9, "bold")).pack(pady=(0, 1))
    ctk.CTkLabel(patch, text="감수하시고 사용하시고 6개월째 제것만 정지 없습니다.",
                 text_color="#a6adc8", font=("Malgun Gothic", 9)).pack(pady=(0, 1))
    ctk.CTkLabel(patch, text="항상 후원 감사합니다. ❤️",
                 text_color="#f9e2af", font=("Malgun Gothic", 9)).pack(pady=(0, 6))

    sf = ctk.CTkScrollableFrame(patch, fg_color="#1e1e2e", corner_radius=8, width=430, height=300)
    sf.pack(fill="both", expand=True, padx=10, pady=(0, 6))
    for item in LATEST_PATCH:
        ctk.CTkLabel(sf, text="[NEW] " + item, text_color="#a6e3a1", font=("Malgun Gothic", 10, "bold"),
                     wraplength=400, justify="left").pack(anchor="w", pady=(4, 0), padx=8)
    ctk.CTkLabel(sf, text="", height=4).pack()
    ctk.CTkLabel(sf, text="━" * 50, text_color="#45475a", font=("", 6)).pack(pady=6)
    ctk.CTkLabel(sf, text="지난 업데이트", text_color="#89b4fa", font=("Malgun Gothic", 11, "bold")).pack(anchor="w", padx=8, pady=(0, 4))
    for item in PAST_PATCHES:
        ctk.CTkLabel(sf, text=item, text_color="#6c7086", font=("Malgun Gothic", 9),
                     wraplength=400, justify="left").pack(anchor="w", pady=(2, 0), padx=8)

    ctk.CTkButton(patch, text="닫기", command=patch.destroy, fg_color="#800020", hover_color="#9e1a3a",
                  text_color="#ffffff", font=("Malgun Gothic", 12, "bold")).pack(pady=10)

def stop_everything(reason="💤 대기 중"):
    global running, ser, root, chk_follow, chk_fix, lbl_status
    running = False; time.sleep(0.05) 
    if root:
        if chk_follow and chk_follow.get():
            if ser and ser.is_open:
                try: time.sleep(0.02); ser.write(b'T') 
                except: pass
            root.after(0, lambda: chk_follow.set(False))
        if chk_fix and chk_fix.get():
            if ser and ser.is_open:
                try: time.sleep(0.05); ser.write(b'U'); time.sleep(0.1) 
                except: pass
            root.after(0, lambda: chk_fix.set(False))
        if lbl_status: root.after(0, lambda: lbl_status.configure(text=reason, text_color="#f38ba8"))
    try: keyboard.release('shift'); time.sleep(0.01)
    except: pass
    if ser and ser.is_open:
        try: time.sleep(0.05); ser.write(b'U'); time.sleep(0.1) 
        except: pass

def get_safe_int(var, default=1200):
    try: return int(var.get())
    except: return default

def update_ui_timer():
    global running, root, lbl_buff, lbl_status
    global last_buff_seq, BUFF_SEQ_GAP, last_auth_check, loaded_pwd, last_log, lbl_log
    global shutdown_time, lbl_auth, saved_expire_start, saved_expire_days
    global chk_buff_on, _buff_cfg, buff_next_due, last_buff_global
    while True:
        if root and lbl_auth:
            auth_text = ""
            if saved_expire_start and saved_expire_days and saved_expire_days != "0":
                try:
                    start_dt = datetime.strptime(saved_expire_start, "%Y-%m-%d")
                    days_left = int(saved_expire_days) - (datetime.now() - start_dt).days
                    if days_left < 0: days_left = 0
                    from datetime import timedelta as td
                    expire_dt = start_dt + td(days=int(saved_expire_days))
                    auth_text = f"🔑 {days_left}일 남음 ({expire_dt.strftime('%m/%d')} 만료)"
                except: auth_text = "🔑 영구 사용"
            elif loaded_pwd: auth_text = "🔑 영구 사용"
            root.after(0, lambda t=auth_text: lbl_auth.configure(text=t))
        if root and lbl_log and running and last_log:
            txt = last_log
            def _upd(t=txt):
                lbl_log.configure(state="normal")
                lbl_log.delete("1.0", "end")
                lbl_log.insert("1.0", t)
                lbl_log.see("end")
                lbl_log.configure(state="disabled")
            root.after(0, _upd)
        # 30분마다 구글시트 재검증
        now_ts = time.time()
        if running and loaded_pwd and (now_ts - last_auth_check > 300):
            last_auth_check = now_ts
            cs_result, cs_info, _ = check_google_sheet(loaded_pwd)
            if cs_result in ("NOT_FOUND", "ERROR", "ALREADY_IN_USE"):
                time.sleep(2)
                cs_result, cs_info, _ = check_google_sheet(loaded_pwd)
                if cs_result in ("NOT_FOUND", "ERROR", "ALREADY_IN_USE"):
                    stop_everything("인증 만료"); continue
            if cs_info == "0":
                stop_everything("코드 만료"); continue
        if running:
            now = time.time(); txt_parts = []
            gap_remain = max(0, int(BUFF_SEQ_GAP - (now - last_buff_seq)))
            if chk_buff_on and chk_buff_on.get():
                for hb in BUFF_HOTBARS:
                    for slot, cb, iv in _buff_cfg.get(hb, []):
                        if not cb.get():
                            continue
                        tk = buff_time_key(hb, slot)
                        due = buff_next_due.get(tk, now)
                        remain = max(max(0, int(due - now)), gap_remain)
                        hb_tag = hb if hb != "F1" else "F1"
                        txt_parts.append(f"▶ {hb_tag}-{slot}: {remain}초")
            if shutdown_time is not None:
                rem = int(shutdown_time - now)
                if rem > 0: rh = rem // 3600; rm = (rem % 3600) // 60; rs = rem % 60; txt_parts.append(f"⏰ 예약 : {rh:02d}시 {rm:02d}분 {rs:02d}초")
                else: txt_parts.append("⏰ 예약종료...!")
            if txt_parts and root and lbl_buff: root.after(0, lambda t="\n".join(txt_parts): lbl_buff.configure(text=f"✨ 버프 대기 ✨\n{t}", text_color='#a6e3a1'))
            elif root and lbl_buff: root.after(0, lambda: lbl_buff.configure(text=""))
        time.sleep(1)

def on_space_save(e=None):
    global debounce, chk_space_save, running, camera, root, lbl_saved_coord
    if not chk_space_save or not chk_space_save.get(): return
    if time.time() - debounce['space'] < 0.5: return
    debounce['space'] = time.time()
    if not running:
        pt = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)); cx, cy = pt.x, pt.y
        try:
            frame = camera.get_latest_frame() if camera else None
            r, g, b = get_rgb(frame, cx, cy) if frame is not None else (0,0,0)
        except: r, g, b = 0, 0, 0
        with open(COORD_FILE, 'a', encoding='utf-8') as f: f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{cx},{cy},{r},{g},{b}\n") 

def on_caps_lock(e=None):
    global debounce, ser, running, chk_follow, root
    if time.time() - debounce['caps'] < 0.15: return 
    debounce['caps'] = time.time()
    if ser and ser.is_open and running: 
        ser.write(b'T')
        try: keyboard.release('shift'); time.sleep(0.01)
        except: pass
        if root and chk_follow: root.after(0, lambda: chk_follow.set(not chk_follow.get()))

def on_tab_toggle(e=None):
    global debounce, ser, running, chk_fix, root, chk_follow
    if time.time() - debounce['tab'] < 0.15: return 
    debounce['tab'] = time.time()
    if ser and ser.is_open and running:
        is_fixed = not chk_fix.get() if chk_fix else False
        if is_fixed: ser.write(b'H') 
        else: 
            ser.write(b'U')
            if chk_follow and chk_follow.get(): time.sleep(0.04); ser.write(b'T')
        if root and chk_fix: root.after(0, lambda: chk_fix.set(is_fixed))

def on_f4_toggle(e=None):
    global debounce, chk_loot, root, last_loot_sent_time
    if last_loot_sent_time and time.time() - last_loot_sent_time < 1.0: return
    if time.time() - debounce['f4'] < 0.15: return 
    debounce['f4'] = time.time()
    if root and chk_loot: root.after(0, lambda: chk_loot.set(not chk_loot.get()))

def on_main_toggle(e=None):
    global running, last_buff_seq, debounce, root, lbl_status
    global last_loot, loot_interval, buff_next_due, last_buff_global
    global last_self_heal, last_party_heal, last_noparty_heal
    if time.time() - debounce['main'] < 0.25: return 
    debounce['main'] = time.time()
    if not running:
        connect_hardware()
        if not ser or not getattr(ser, "is_open", False):
            _hw = hw_var.get() if ('hw_var' in globals() and hw_var) else HW_MODE
            msg = "○ 뚱박스 연결실패" if _hw in ("뚱박스", "KMBox") else "○ 장치 연결실패"
            if root and lbl_status:
                root.after(0, lambda m=msg: lbl_status.configure(text=m, text_color="#f85149"))
            if root and lbl_ard:
                root.after(0, lambda m=msg: lbl_ard.configure(text=m, text_color="#f85149"))
            return
        running = True; now = time.time()
        last_loot = now; loot_interval = random.uniform(4.0, 7.0)
        last_buff_seq = now
        last_buff_global = now
        for hb in BUFF_HOTBARS:
            for slot, cb, iv in _buff_cfg.get(hb, []):
                if cb.get():
                    schedule_buff(buff_time_key(hb, slot), get_safe_int(iv, BASE_BUFF_INTERVAL), soon=True)
        last_self_heal = now
        last_party_heal = now
        last_noparty_heal = now
        if root and lbl_status: root.after(0, lambda: lbl_status.configure(text="🟢 시스템 정상 가동 중", text_color="#a6e3a1"))
    else: stop_everything()

def reserve_shutdown_worker():
    global shutdown_time, timer_thread_active, running, root, ser
    while timer_thread_active:
        if shutdown_time is not None:
            if time.time() >= shutdown_time:
                if ser and ser.is_open:
                    try: ser.write(b'C'); ser.flush()
                    except: pass
                    time.sleep(4.0) 
                stop_everything("⏰ 자동 차단 정지 완료")
                time.sleep(0.5)
                if root: root.after(100, exit_app)
                break
        time.sleep(1.0)

def set_shutdown_timer(value):
    global shutdown_time
    if value == "예약OFF" or value == "예약오프": shutdown_time = None
    else:
        try: shutdown_time = time.time() + int(value.replace("시간", "").strip()) * 3600
        except: shutdown_time = None

def ensure_kmnet():
    """뚱박스용 kmNet.pyd 가 없으면 GitHub에서 파이썬 버전에 맞는 걸 자동 다운로드 후 로드."""
    global kmNet
    if kmNet is not None and hasattr(kmNet, "lcd_picture"):
        return True
    if kmNet is None:
        try:
            import kmNet as _k; kmNet = _k
        except ImportError:
            pass
        if kmNet is not None and hasattr(kmNet, "lcd_picture"):
            return True
    try:
        import ssl, importlib
        ver = f"cp{sys.version_info.major}{sys.version_info.minor}"
        fname = f"kmNet.{ver}-win_amd64.pyd"
        dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        # lcd_picture(LCD 이미지) 함수가 있는 2024-05-27 버전. 최신 릴리스판은 이 함수가 빠져있음.
        urls = [
            f"https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/{fname}",
            f"https://raw.githubusercontent.com/kvmaibox/kmboxnet/e5bfcd00652c4ee00b2125829c52bf8c6349a6c5/python_pyd/{fname}",
        ]
        got = False
        for u in urls:
            try:
                data = urllib.request.urlopen(u, context=ctx, timeout=30).read()
                if len(data) > 10000:
                    if os.path.exists(dest):
                        try: ctypes.windll.kernel32.SetFileAttributesW(dest, 128)
                        except: pass
                    with open(dest, "wb") as f: f.write(data)
                    try: ctypes.windll.kernel32.SetFileAttributesW(dest, 2)   # 숨김 속성
                    except: pass
                    got = True; break
            except: continue
        if not got: return False
        importlib.invalidate_caches()
        if kmNet is None:
            try: import kmNet as _k; kmNet = _k
            except: pass
        return kmNet is not None
    except Exception:
        return False

def ensure_logo():
    """뚱박스 LCD 로고(뚱힐러.gif) 없으면 GitHub에서 자동 다운로드(숨김) 후 프레임 로드."""
    global _logo_frames, _logo_delay
    if _logo_frames:
        return True
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "뚱힐러.gif")
        if not os.path.exists(path):
            import ssl
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            for u in ["https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/%EB%9A%B1%ED%9E%90%EB%9F%AC.gif"]:
                try:
                    data = urllib.request.urlopen(u, context=ctx, timeout=30).read()
                    if len(data) > 1000:
                        with open(path, "wb") as f: f.write(data)
                        try: ctypes.windll.kernel32.SetFileAttributesW(path, 2)
                        except: pass
                        break
                except: continue
        if not os.path.exists(path):
            return False
        im = Image.open(path)
        _logo_delay = (im.info.get("duration") or 80) / 1000.0
        fr = []
        for i in range(getattr(im, "n_frames", 1)):
            im.seek(i)
            arr = np.array(im.convert("RGB").resize((128, 160)), dtype=np.uint8)[:, :, ::-1]  # RGB→BGR
            fr.append(np.ascontiguousarray(arr).flatten())
        _logo_frames = fr
        return True
    except Exception:
        return False

def lcd_logo_worker():
    """사냥 중(running)일 때만 뚱박스 LCD에 로고 애니 재생. 멈추면 박스 정보 놔둠."""
    while True:
        try:
            if running and _logo_frames and ser is not None and getattr(ser, "is_open", False) and hasattr(ser, "lcd"):
                for f in _logo_frames:
                    if not running: break
                    ser.lcd(f)
                    time.sleep(_logo_delay)
            else:
                time.sleep(0.3)
        except Exception:
            time.sleep(0.3)

def connect_hardware():
    """하드웨어 연결 (드롭다운 선택에 따라 아두이노/KMBox). 재연결에도 재사용."""
    global ser
    try:
        if ser: ser.close()
    except: pass
    ser = None
    try:
        _hw = hw_var.get() if ('hw_var' in globals() and hw_var) else HW_MODE
        if _hw in ("뚱박스", "KMBox"):
            if kmNet is None or not hasattr(kmNet, "lcd_picture"):
                if root and lbl_ard: root.after(0, lambda: lbl_ard.configure(text="⬇ 뚱박스 드라이버 받는중", text_color='#f9e2af'))
                if not ensure_kmnet():
                    if root and lbl_ard: root.after(0, lambda: lbl_ard.configure(text="○ kmNet 없음", text_color='#f85149'))
                    return
            _kip = ent_km_ip.get().strip() if ('ent_km_ip' in globals() and ent_km_ip and ent_km_ip.get().strip()) else KM_IP
            _kport = ent_km_port.get().strip() if ('ent_km_port' in globals() and ent_km_port and ent_km_port.get().strip()) else KM_PORT
            _kmac = ent_km_mac.get().strip() if ('ent_km_mac' in globals() and ent_km_mac and ent_km_mac.get().strip()) else KM_MAC
            globals()['KM_IP'] = _kip; globals()['KM_PORT'] = _kport; globals()['KM_MAC'] = _kmac
            ser = KmBox(_kip, _kport, _kmac)
            try: ensure_logo()
            except: pass
            if root and lbl_ard: root.after(0, lambda ip=_kip: lbl_ard.configure(text=f"● 뚱박스 {ip}", text_color='#3fb950'))
        else:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
            if root and lbl_ard: root.after(0, lambda: lbl_ard.configure(text=f"● {SERIAL_PORT}", text_color='#3fb950'))
    except Exception:
        ser = None
        if root and lbl_ard: root.after(0, lambda: lbl_ard.configure(text="○ 연결실패", text_color='#f85149'))

def expert_logic():
    global ser, running, last_buff_seq, BUFF_SEQ_GAP
    global last_loot, last_loot_sent_time, loot_interval
    global camera, root, lbl_ard, mode_var, chk_follow, current_f9_prob
    global chk_loot, chk_poison, chk_target_poison, chk_party_poison, chk_buff_on
    global SELF_HP_COORD, SELF_HP_RGB, NOPARTY_HP_COORD, NOPARTY_RGB, PARTY_COORDS, MAIN_ATTACKER_COORD
    global DANGER_HP_COORD, DANGER_HP_RGB, SELF_POISON_COORD, SELF_POISON_RGB, TARGET_POISON_COORD, TARGET_POISON_RGB
    global last_self_heal, last_party_heal, last_party_cure, last_noparty_heal
    global party_mode_flags, selected_party_flags
    global SELF_HP_ROI, SELF_HP_100_REF, DANGER_HP_ROI, DANGER_HP_100_REF
    global self_hp_threshold, danger_hp_threshold, attacker_hp_threshold, mna_threshold, strong_heal_pct, chk_strong_heal
    global attacker_hp_udp, attacker_poisoned, attacker_petrified
    global MNA_ROI, MNA_100_REF, last_mna_potion, chk_mna, chk_self_heal_sw, chk_danger_sw, chk_attacker_sw
    global buff_next_due, last_buff_global, _buff_cfg
    
    load_buff_templates()

    while True:
        now = time.time()
        if _reconnect_req and not running:
            globals()['_reconnect_req'] = False
            connect_hardware()
        if running and ser and getattr(ser, 'is_open', False):
            frame = camera.get_latest_frame() if camera else None
            if frame is None: time.sleep(0.01); continue 

            # 위험베르 — 최우선 (HP%만 판정, 빨강/초록 독 무관)
            danger_roi = DANGER_HP_ROI if DANGER_HP_ROI[0] != 0 else SELF_HP_ROI
            danger_ref = DANGER_HP_100_REF if DANGER_HP_ROI[0] != 0 else SELF_HP_100_REF
            if danger_roi[0] != 0:
                # 전체화면 프레임을 잘라쓰지 않고, 미리보기와 동일하게 ROI만 직접 캡처
                # (모니터 오프셋 등으로 전체화면 슬라이싱이 실제 화면과 어긋날 가능성 제거)
                _danger_arr = camera.grab_roi(danger_roi) if camera else None
                danger_pct = _self_hp_pct_from_arr(_danger_arr, danger_ref) if _danger_arr is not None else self_hp_pct(frame, danger_roi, danger_ref)
                # 순간적으로 크게 뚝 떨어지는 순간(예: 40->6%)을 자동으로 감지해서
                # 그 프레임의 실제 픽셀을 파일로 남긴다 — 추측이 아니라 실제 데이터로
                # 원인을 확인하기 위한 진단용 스냅샷(과도한 저장 방지용 쿨다운 2초).
                global _last_selfhp_debug_pct, _last_selfhp_debug_time
                if (_last_selfhp_debug_pct - danger_pct >= 15) and (now - _last_selfhp_debug_time >= 2.0):
                    _dbg_summary = _debug_dump_self_hp(_danger_arr, danger_roi, danger_ref, danger_pct, _last_selfhp_debug_pct)
                    _last_selfhp_debug_time = now
                    # 파일이 아니라 화면 로그에 바로 판정과정을 찍음 — 배포판 다른 컴퓨터에서도
                    # 화면 캡처(스크린샷)만 보내주면 원인 확인 가능하게.
                    log_event(f"🩻 HP급락 {_last_selfhp_debug_pct:.0f}%→{danger_pct:.0f}% {_dbg_summary or ''}")
                _last_selfhp_debug_pct = danger_pct
                # 연속프레임 확인(디바운스)은 제거함 — 전투 이펙트로 매 프레임 픽셀이
                # 미세하게 흔들리면 "연속으로 낮게"가 오히려 잘 안 걸려서, 진짜 위험한
                # 순간에 위기베르가 발동을 안 하는 훨씬 위험한 문제가 생겼음(생명과 직결).
                # 한 프레임 오독으로 어쩌다 한번 더 발동하는 것보다, 위험할 때 반드시
                # 발동하는 쪽이 훨씬 중요하므로 즉시발동으로 원복.
                if chk_danger_sw.get() and danger_pct < danger_hp_threshold:
                    ser.write(b'C'); log_event(f"🛡️ 위험베르 (HP:{danger_pct:.0f}%)"); stop_everything(f"🚨 위기 베르 감지 (HP:{danger_pct:.0f}%)"); continue

            # 줍기
            if chk_loot and chk_loot.get() and (now - last_loot >= loot_interval):
                last_loot_sent_time = now; ser.write(b'4'); last_loot = now; loot_interval = random.uniform(4.0, 7.0); log_event('🎒 줍기') 

            # 마나 물약
            if chk_mna and chk_mna.get() and MNA_ROI[0] != 0 and (now - last_mna_potion >= 600):
                mna_pct = roi_mna_pct(frame, MNA_ROI, MNA_100_REF)
                if mna_pct < mna_threshold:
                    execute_keys(['2', '8', '1'], 0.5); last_mna_potion = now
                    log_event(f"💙 마나물약 (MP:{mna_pct:.0f}%)")
                    continue

            m = mode_var.get() if mode_var else "파티"

            # ── 해독 ──────────────────────────────────────
            # 쫄법 독:   F2→F9(엔줄고정)→F1
            # 격수 독:   F2→F10(큐어포이즌)→F1 (UDP)
            # 파티 독:   파티창 클릭 → F2→F10(큐어포이즌)→F1 (격수해독과 동일)
            # 쫄법 석화: F2→F12(리무브커스)→F1 (ROI)
            # 격수 석화: F2→F12(리무브커스)→F1 (UDP)
            if chk_poison and chk_poison.get() and is_green_bar(frame, SELF_HP_ROI):
                fix_mode_keys(['2', '9', '1'], 0.5); log_event('🟢 독해독'); continue
            if chk_target_poison and chk_target_poison.get() and attacker_poisoned:
                # 노파티: HP 임계값 미만이면 해독보다 힐 우선 (독이어도 HP%만 본다)
                udp_fresh = (time.time() - last_udp_time) < 5
                atk_hp = attacker_hp_udp
                hp_need_heal = udp_fresh and atk_hp < attacker_hp_threshold
                if not (m == "노파티" and hp_need_heal):
                    fix_mode_keys(['2', 'X', '1'], 0.45); attacker_poisoned = False; log_event('🟢 격수 독해독'); continue
            if chk_party_poison and chk_party_poison.get() and (now - last_party_cure >= 0.5):
                party_flags = party_mode_flags if m == "파티" else selected_party_flags
                cure_pi = -1; cure_tx = 0; cure_ty = 0
                for pi in range(1, 8):
                    if not party_flags[pi]: continue
                    if PARTY_ROIS[pi][0] <= 0: continue
                    if not party_slot_active(frame, PARTY_ROIS[pi]): continue
                    if is_green_bar(frame, PARTY_ROIS[pi]):
                        x1, y1, x2, y2 = PARTY_ROIS[pi]
                        cure_pi = pi; cure_tx, cure_ty = (x1 + x2) // 2, (y1 + y2) // 2
                        break
                if cure_pi >= 0:
                    if m == "파티":
                        pt_orig = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt_orig))
                        orig_x, orig_y = pt_orig.x, pt_orig.y
                        was_auto = chk_follow.get() if chk_follow else False
                        if was_auto: ser.write(b'T'); time.sleep(0.03)
                        human_mouse_move(cure_tx + random.randint(-3, 3), cure_ty + random.randint(-2, 2)); time.sleep(0.02)
                        fix_mode_keys(['2', 'X', '1'], 0.45)
                        human_mouse_move(orig_x + random.randint(-2, 2), orig_y + random.randint(-2, 2))
                        if was_auto: ser.write(b'T'); time.sleep(0.03)
                    else:
                        fix_mode_keys(['2', 'X', '1'], 0.45)
                    last_party_cure = now; log_event(f'🟢 파티해독 P{cure_pi + 1}'); continue

            # 버프 (F1/F2/F3 × F5~F12 그리드)
            if chk_buff_on and chk_buff_on.get() and (now - last_buff_global >= 1.0) and (now - last_buff_seq >= BUFF_SEQ_GAP):
                buff_cast = False
                for hb in BUFF_HOTBARS:
                    for slot, cb, iv in _buff_cfg.get(hb, []):
                        if not cb.get():
                            continue
                        tk = buff_time_key(hb, slot)
                        iv_sec = get_safe_int(iv, BASE_BUFF_INTERVAL)
                        if now >= buff_next_due.get(tk, 0):
                            cast_buff(hb, slot)
                            schedule_buff(tk, iv_sec, soon=False)
                            last_buff_seq = now
                            last_buff_global = now
                            tag = f"{hb}-{slot}" if hb != "F1" else slot
                            log_event(f"✨ 버프 {tag}")
                            buff_cast = True
                            break
                    if buff_cast:
                        break
                if buff_cast:
                    continue

            # MP% 체크 (자힐 제한)
            _mp_low = False
            if chk_mna and chk_mna.get() and MNA_ROI[0] != 0:
                _mp_low = roi_mna_pct(frame, MNA_ROI, MNA_100_REF) < mna_threshold

            # 솔로(파티)
            if m == "솔로(파티)":
                healed = False
                if SELF_HP_ROI[0] != 0:
                    self_hp = roi_hp_pct(frame, SELF_HP_ROI, SELF_HP_100_REF)
                    if chk_self_heal_sw.get() and self_hp < self_hp_threshold and (now - last_self_heal >= 0.3):
                        prob = int(current_f9_prob * 100)
                        if _mp_low: prob = 0
                        if prob == 0: execute_keys(['E'], 1.0, skip_follow_toggle=True)
                        elif prob >= 100: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                        else:
                            if random.randint(1, 100) <= prob: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                            else: execute_keys(['E'], 1.0, skip_follow_toggle=True)
                        last_self_heal = now; healed = True; log_event(f'🔴 자힐 ({int(self_hp)}%)')
                elif chk_self_heal_sw.get() and chk_color(frame, SELF_HP_COORD, SELF_HP_RGB, 18) and (now - last_self_heal >= 0.3):
                    prob = int(current_f9_prob * 100)
                    if _mp_low: prob = 0
                    if prob == 0: execute_keys(['E'], 1.0, skip_follow_toggle=True)
                    elif prob >= 100: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                    else:
                        if random.randint(1, 100) <= prob: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                        else: execute_keys(['E'], 1.0, skip_follow_toggle=True)
                    last_self_heal = now; healed = True; log_event(f'🔴 자힐 ({int(self_hp)}%)')

                if not healed:
                    best_i = -1; best_hp = 999
                    for i in range(8):
                        if selected_party_flags[i] and PARTY_ROIS[i][0] != 0:
                            hp_pct = scan_party_hp(frame, i)
                            if hp_pct is not None and hp_pct > 1.0 and hp_pct < PARTY_HP_THRESHOLDS[i]:
                                if hp_pct < best_hp:
                                    best_hp = hp_pct; best_i = i
                    if best_i >= 0:
                        if chk_strong_heal and chk_strong_heal.get() and best_hp < strong_heal_pct:
                            ser.write(b'7'); log_event(f"⚡ 상위힐 P{best_i+1} HP{best_hp:.0f}%")
                        else:
                            ser.write(b'A')
                        time.sleep(human_delay(1.2, 1.6)); healed = True
                    if healed: continue

            # 파티
            elif m == "파티":
                healed = False
                if SELF_HP_ROI[0] != 0:
                    self_hp = roi_hp_pct(frame, SELF_HP_ROI, SELF_HP_100_REF)
                    if chk_self_heal_sw.get() and self_hp < self_hp_threshold and (now - last_self_heal >= 0.3):
                        prob = int(current_f9_prob * 100)
                        if _mp_low: prob = 0
                        if prob == 0: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                        elif prob >= 100: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                        else:
                            if random.randint(1, 100) <= prob: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                            else: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                        last_self_heal = now; healed = True; log_event(f'🔴 자힐 ({int(self_hp)}%)')
                elif chk_self_heal_sw.get() and chk_color(frame, SELF_HP_COORD, SELF_HP_RGB, 18) and (now - last_self_heal >= 0.3):
                    prob = int(current_f9_prob * 100)
                    if _mp_low: prob = 0
                    if prob == 0: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                    elif prob >= 100: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                    else:
                        if random.randint(1, 100) <= prob: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                        else: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                    last_self_heal = now; healed = True; log_event(f'🔴 자힐 ({int(self_hp)}%)')

                if not healed:
                    pt_orig = POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt_orig))
                    orig_x, orig_y = pt_orig.x, pt_orig.y
                    best_pi = -1; best_hp = 999; best_tx = 0; best_ty = 0
                    for pi in range(1, 8):
                        if not party_mode_flags[pi]: continue
                        if PARTY_ROIS[pi][0] > 0:
                            hp_pct = scan_party_hp(frame, pi)
                            if hp_pct is not None and hp_pct > 1.0 and hp_pct < PARTY_HP_THRESHOLDS[pi]:
                                if hp_pct < best_hp:
                                    best_hp = hp_pct; best_pi = pi
                                    x1,y1,x2,y2 = PARTY_ROIS[pi]
                                    best_tx, best_ty = (x1+x2)//2, (y1+y2)//2
                    if best_pi >= 0:
                        was_auto = chk_follow.get() if chk_follow else False
                        if was_auto: ser.write(b'T'); time.sleep(0.03)
                        human_mouse_move(best_tx + random.randint(-3, 3), best_ty + random.randint(-2, 2)); time.sleep(0.02)
                        use_strong = chk_strong_heal and chk_strong_heal.get() and best_hp < strong_heal_pct
                        heal_key = '7' if use_strong else 'A'
                        execute_keys(['K', 'K', heal_key, 'K', 'K'], 0.15, skip_follow_toggle=True)
                        human_mouse_move(orig_x + random.randint(-2, 2), orig_y + random.randint(-2, 2))
                        if was_auto: ser.write(b'T'); time.sleep(0.03)
                        last_party_heal = now; healed = True
                        if use_strong:
                            log_event(f"⚡ 상위힐 P{best_pi + 1} HP{best_hp:.0f}%")

            # 노파티 — 격수힐: 독 여부와 무관, UDP HP% vs 격수% 임계값만 판단
            elif m == "노파티":
                action_taken = False
                if SELF_HP_ROI[0] != 0:
                    self_hp = roi_hp_pct(frame, SELF_HP_ROI, SELF_HP_100_REF)
                    if chk_self_heal_sw.get() and self_hp < self_hp_threshold and (now - last_self_heal >= 0.2):
                        prob = int(current_f9_prob * 100)
                        if _mp_low: prob = 0
                        if prob == 0: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                        elif prob >= 100: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                        else:
                            if random.randint(1, 100) <= prob: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                            else: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                        last_self_heal = now; action_taken = True
                elif chk_self_heal_sw.get() and chk_color(frame, SELF_HP_COORD, SELF_HP_RGB, 20) and (now - last_self_heal >= 0.2):
                    prob = int(current_f9_prob * 100)
                    if _mp_low: prob = 0
                    if prob == 0: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                    elif prob >= 100: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                    else:
                        if random.randint(1, 100) <= prob: execute_keys(['B'], 0.5, skip_follow_toggle=True)
                        else: execute_keys(['E'], 0.8, skip_follow_toggle=True)
                    last_self_heal = now; action_taken = True
                
                if not action_taken and (now - last_noparty_heal >= 0.2):
                    udp_ok = (time.time() - last_udp_time) < 5
                    atk_hp = attacker_hp_udp
                    if chk_attacker_sw.get() and udp_ok and atk_hp < attacker_hp_threshold:
                        use_strong = chk_strong_heal and chk_strong_heal.get() and atk_hp < strong_heal_pct
                        if use_strong:
                            ser.write(b'7'); log_event(f"⚡ 상위힐 격수 HP{atk_hp:.0f}%"); time.sleep(human_delay(1.2, 1.6))
                        elif random.randint(1, 100) <= 85:
                            ser.write(b'A'); log_event(f"💚 격수힐 HP{atk_hp:.0f}%"); time.sleep(human_delay(1.2, 1.6))
                        else:
                            time.sleep(human_delay(0.2, 0.3))
                        last_noparty_heal = now

                
        if not running: time.sleep(0.2)
        else:
            if random.randint(1, 100) <= 2:
                try: time.sleep(0.02)
                except: pass
            time.sleep(0.002)

# =======================================================
# 🚨 메인 구동
# =======================================================
root = ctk.CTk()
root.geometry("195x380+0+0")
root.attributes("-topmost", True)
def auto_resize_height():
    if root and root.winfo_exists():
        h = root.winfo_reqheight()
        if h > 200: x = root.winfo_x(); y = root.winfo_y(); root.geometry(f"195x{h}+{x}+{y}")
    root.after(500, auto_resize_height)
root.after(1000, auto_resize_height)
root.configure(fg_color="#141420") 
root.overrideredirect(True) 

title_bar = ctk.CTkFrame(root, height=24, corner_radius=0, fg_color="#141420")
title_bar.pack(fill="x")
try:
    title_text = " 뚱힐러"
    if os.path.exists("logo.png"):
        logo_img = ctk.CTkImage(light_image=Image.open("logo.png"), size=(18, 18))
        title_lbl = ctk.CTkLabel(title_bar, text=title_text, image=logo_img, compound="left", font=("Malgun Gothic", 12, "bold"), text_color="#cba6f7")
    else: title_lbl = ctk.CTkLabel(title_bar, text="❖ 뚱힐러 ❖", font=("Malgun Gothic", 12, "bold"), text_color="#cba6f7")
except: title_lbl = ctk.CTkLabel(title_bar, text="❖ 뚱힐러 ❖", font=("Malgun Gothic", 12, "bold"), text_color="#cba6f7")
title_lbl.place(relx=0.5, rely=0.5, anchor="center") 

def exit_app():
    global timer_thread_active, loaded_pwd
    timer_thread_active = False
    try: save_hidden_config(loaded_pwd if loaded_pwd else "")
    except: pass
    try:
        if camera: camera.stop(); camera.release()
    except: pass
    keyboard.unhook_all(); os._exit(0)

exit_btn = ctk.CTkButton(title_bar, text="✖", width=24, height=20, fg_color="#800020", hover_color="#9e1a3a", border_width=1, border_color="#4a0010", command=exit_app)
exit_btn.pack(side="right", padx=5, pady=2)

def start_move(event): root.x = event.x; root.y = event.y
def stop_move(event): root.x = None; root.y = None
def do_move(event):
    x = root.winfo_x() + (event.x - root.x); y = root.winfo_y() + (event.y - root.y)
    root.geometry(f"+{x}+{y}")
title_bar.bind("<ButtonPress-1>", start_move); title_bar.bind("<ButtonRelease-1>", stop_move); title_bar.bind("<B1-Motion>", do_move)
title_lbl.bind("<ButtonPress-1>", start_move); title_lbl.bind("<ButtonRelease-1>", stop_move); title_lbl.bind("<B1-Motion>", do_move)

def keep_on_top():
    if root: root.attributes("-topmost", True); root.lift(); root.after(2000, keep_on_top)
keep_on_top()

chk_fix = ctk.BooleanVar(value=False)
chk_follow = ctk.BooleanVar(value=False)
chk_space_save = ctk.BooleanVar(value=False) 
mode_var = ctk.StringVar(value="파티")
chk_buff_on = ctk.BooleanVar(value=saved_buff_on in ("1", "true", "True"))
chk_poison = ctk.BooleanVar(value=False)
chk_target_poison = ctk.BooleanVar(value=False)
chk_party_poison = ctk.BooleanVar(value=False)
chk_loot = ctk.BooleanVar(value=False) 
f9_prob_var = ctk.DoubleVar(value=0.3) 

prob_combo = None
def set_f9_prob(val):
    global current_f9_prob
    try: current_f9_prob = float(val.replace("%", "").strip()) / 100.0
    except: current_f9_prob = 0.3

# ─── 상단 헤더바 (업데이트 + COM포트) ───
header = ctk.CTkFrame(root, fg_color="#161b22", corner_radius=8, height=22)
header.pack(pady=(2,1), padx=2, fill='x')
ctk.CTkLabel(header, text=f"업데이트: {PATCH_UPDATED_AT}", text_color="#e2e8f0",
             font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=8, pady=2)
lbl_ard = ctk.CTkLabel(header, text="장치 확인 중...", text_color="#a6adc8",
                        font=("Malgun Gothic", 8, "bold"))
lbl_ard.pack(side="right", padx=8, pady=2)

# ─── 하드웨어 선택 (아두이노/KMBox) + KMBox 접속입력 ───
frame_hw = ctk.CTkFrame(root, fg_color="#161b22", corner_radius=6)
frame_hw.pack(pady=(1,1), padx=2, fill='x')
ctk.CTkLabel(frame_hw, text="장치", text_color="#f9e2af", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(6,3))
hw_var = tk.StringVar(value=HW_MODE)
hw_combo = ctk.CTkComboBox(frame_hw, values=["뚱USB", "뚱박스"], variable=hw_var, width=110, height=22,
                           font=("Malgun Gothic", 9), dropdown_font=("Malgun Gothic", 9),
                           fg_color="#1e1e2e", button_color="#800020", border_width=1, border_color="#45475a",
                           command=lambda v: _toggle_km_fields(v))
hw_combo.pack(side="left", padx=2)

frame_kmfields = ctk.CTkFrame(root, fg_color="#161b22", corner_radius=6)
_kmr1 = ctk.CTkFrame(frame_kmfields, fg_color="transparent"); _kmr1.pack(fill='x', pady=1)
ctk.CTkLabel(_kmr1, text="IP", width=34, anchor="w", text_color="#a6adc8", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(6,2))
ent_km_ip = ctk.CTkEntry(_kmr1, width=132, height=20, font=("Malgun Gothic", 9))
ent_km_ip.pack(side="left"); ent_km_ip.insert(0, KM_IP)
_kmr2 = ctk.CTkFrame(frame_kmfields, fg_color="transparent"); _kmr2.pack(fill='x', pady=1)
ctk.CTkLabel(_kmr2, text="포트", width=34, anchor="w", text_color="#a6adc8", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(6,2))
ent_km_port = ctk.CTkEntry(_kmr2, width=132, height=20, font=("Malgun Gothic", 9))
ent_km_port.pack(side="left"); ent_km_port.insert(0, KM_PORT)
_kmr3 = ctk.CTkFrame(frame_kmfields, fg_color="transparent"); _kmr3.pack(fill='x', pady=1)
ctk.CTkLabel(_kmr3, text="UUID", width=34, anchor="w", text_color="#a6adc8", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(6,2))
ent_km_mac = ctk.CTkEntry(_kmr3, width=132, height=20, font=("Malgun Gothic", 9))
ent_km_mac.pack(side="left"); ent_km_mac.insert(0, KM_MAC)

def _toggle_km_fields(*a):
    if a: globals()['_reconnect_req'] = True   # 사용자가 드롭다운 바꿀 때만 재연결
    if hw_var.get() in ("뚱박스", "KMBox"):
        frame_kmfields.pack(pady=(0,1), padx=2, fill='x', after=frame_hw)
    else:
        frame_kmfields.pack_forget()
_toggle_km_fields()

frame_mode = ctk.CTkFrame(root, fg_color="#313244", corner_radius=6)
frame_mode.pack(pady=(2,1), padx=2, fill='x')
mode_seg = ctk.CTkComboBox(frame_mode, values=["파티", "솔로(파티)", "노파티"], variable=mode_var, width=82, height=32, font=('Malgun Gothic', 11, 'bold'), dropdown_font=('Malgun Gothic', 10), corner_radius=8, fg_color="#1e1e2e", button_color="#800020", border_width=1, border_color="#45475a")
mode_seg.pack(side='left', pady=2, padx=4)
prob_combo = ctk.CTkComboBox(frame_mode, values=["0%", "30%", "50%", "70%", "100%"], command=set_f9_prob, width=82, height=32, font=('Malgun Gothic', 11, 'bold'), dropdown_font=('Malgun Gothic', 10), fg_color="#1e1e2e", button_color="#800020", corner_radius=6, border_width=1, border_color="#45475a")
prob_combo.pack(side='right', pady=2, padx=4)
prob_combo.set("30%")

# ─── 접이식: 옵션 ───
coll_opt = Collapsible(root, "옵션", start_open=False)
coll_opt.pack(pady=1, padx=2, fill="x")
frame_opt = coll_opt.body
frame_opt.grid_columnconfigure(0, weight=1)
frame_opt.grid_columnconfigure(1, weight=1)
sw_w, sw_h = 28, 14; ft = ('Malgun Gothic', 8, 'bold')

RoundedToggle(frame_opt, "고정(PgUp)", "#a371f7", var=chk_fix).grid(row=0, column=0, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "클릭(Home)", "#a371f7", var=chk_follow).grid(row=0, column=1, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "독 해독", "#a371f7", var=chk_poison, cmd=lambda: log_event(f"☠️ 독해독 {'ON' if chk_poison.get() else 'OFF'}")).grid(row=1, column=0, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "격수 해독", "#a371f7", var=chk_target_poison, cmd=lambda: log_event(f"⚔️ 격수해독 {'ON' if chk_target_poison.get() else 'OFF'}")).grid(row=1, column=1, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "파티 해독", "#a371f7", var=chk_party_poison, cmd=lambda: log_event(f"💚 파티해독 {'ON' if chk_party_poison.get() else 'OFF'}")).grid(row=2, column=0, padx=3, pady=2, sticky="w")
RoundedToggle(frame_opt, "줍기(F4)", "#a371f7", var=chk_loot, cmd=lambda: log_event(f"🎒 줍기 {'ON' if chk_loot.get() else 'OFF'}")).grid(row=2, column=1, padx=3, pady=2, sticky="w")

# ─── 접이식: 버프 그리드 ───
coll_buff = Collapsible(root, "버프", start_open=False)
coll_buff.pack(pady=1, padx=2, fill="x")
buff_body = coll_buff.body
RoundedToggle(buff_body, "버프 자동", "#a371f7", var=chk_buff_on, cmd=lambda: log_event(f"✨ 버프 {'ON' if chk_buff_on.get() else 'OFF'}")).pack(anchor="w", padx=4, pady=(4, 2))

buff_hotbar_var = tk.StringVar(value="F1")
buff_bar_row = ctk.CTkFrame(buff_body, fg_color="transparent")
buff_bar_row.pack(fill="x", padx=4, pady=2)
ctk.CTkLabel(buff_bar_row, text="단축창", text_color="#a6adc8", font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(0, 4))
buff_hotbar_combo = ctk.CTkComboBox(buff_bar_row, values=BUFF_HOTBARS, variable=buff_hotbar_var, width=52, height=22,
                                    font=("Malgun Gothic", 9), dropdown_font=("Malgun Gothic", 9),
                                    fg_color="#1e1e2e", button_color="#800020")
buff_hotbar_combo.pack(side="left")

buff_page_host = ctk.CTkFrame(buff_body, fg_color="transparent")
buff_page_host.pack(fill="x", padx=2, pady=(0, 4))
_buff_pages = {}

def _parse_buff_saved(hb, slot):
    raw = saved_buff_grid.get(buff_grid_key(hb, slot), f"0:{BASE_BUFF_INTERVAL}")
    parts = raw.split(":", 1)
    on = parts[0] in ("1", "true", "True") if parts else False
    sec = parts[1] if len(parts) > 1 else str(BASE_BUFF_INTERVAL)
    return on, sec

for hb in BUFF_HOTBARS:
    page = ctk.CTkFrame(buff_page_host, fg_color="transparent")
    _buff_pages[hb] = page
    rows = []
    for ri, slots in enumerate([BUFF_SLOT_LABELS[:4], BUFF_SLOT_LABELS[4:]]):
        for ci, slot in enumerate(slots):
            cell = ctk.CTkFrame(page, fg_color="transparent")
            cell.grid(row=ri, column=ci, padx=1, pady=1, sticky="n")
            on_def, sec_def = _parse_buff_saved(hb, slot)
            cb = ctk.BooleanVar(value=on_def)
            iv = tk.StringVar(value=sec_def)
            ctk.CTkCheckBox(cell, text=slot, variable=cb, width=42, checkbox_width=14, checkbox_height=14,
                            font=("Malgun Gothic", 8, "bold"), text_color="#cdd6f4",
                            fg_color="#800020", hover_color="#9e1a3a").pack()
            ent = ctk.CTkEntry(cell, textvariable=iv, width=34, height=18, font=("Malgun Gothic", 8),
                               text_color="#ffffff", fg_color="#1e1e2e", justify="center")
            ent.pack(pady=(0, 1))
            ctk.CTkLabel(cell, text="초", text_color="#6c7086", font=("Malgun Gothic", 7)).pack()
            rows.append((slot, cb, iv))
    _buff_cfg[hb] = rows

def _show_buff_page(choice=None):
    hb = choice or buff_hotbar_var.get()
    for name, page in _buff_pages.items():
        if name == hb:
            page.pack(fill="x")
        else:
            page.pack_forget()

buff_hotbar_combo.configure(command=_show_buff_page)
_show_buff_page("F1")

# ─── 접이식: 힐·물약 ───
coll_heal = Collapsible(root, "힐·물약", start_open=False)
coll_heal.pack(pady=1, padx=2, fill="x")
heal_body = coll_heal.body

frame_selfhp = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_selfhp.pack(pady=1, padx=2, fill='x')
chk_self_heal_sw = ctk.BooleanVar(value=True)
RoundedToggle(frame_selfhp, "🔴 자힐", "#58a6ff", var=chk_self_heal_sw, cmd=lambda: log_event(f"🔴 자힐 {'ON' if chk_self_heal_sw.get() else 'OFF'}")).pack(side='left', padx=5)
self_hp_var = ctk.IntVar(value=self_hp_threshold)
self_hp_sld = ctk.CTkSlider(frame_selfhp, from_=10, to=90, variable=self_hp_var, width=70, height=18, corner_radius=9, fg_color="#21262d", button_color="#10b981", button_hover_color="#34d399", progress_color="#f38ba8")
self_hp_sld.pack(side='left', padx=2)
self_hp_lbl = ctk.CTkLabel(frame_selfhp, text=f"{self_hp_threshold}%", text_color="#f38ba8", font=('Malgun Gothic', 10, 'bold'), width=28)
self_hp_lbl.pack(side='left')
def update_self_hp_thr(*a):
    global self_hp_threshold
    self_hp_threshold = self_hp_var.get(); self_hp_lbl.configure(text=f"{self_hp_threshold}%")
    save_hidden_config(loaded_pwd)
self_hp_var.trace_add("write", update_self_hp_thr)

frame_dangerhp = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_dangerhp.pack(pady=1, padx=2, fill='x')
chk_danger_sw = ctk.BooleanVar(value=True)
RoundedToggle(frame_dangerhp, "🛡️ 위기", "#58a6ff", var=chk_danger_sw, cmd=lambda: log_event(f"🛡️ 위기 {'ON' if chk_danger_sw.get() else 'OFF'}")).pack(side='left', padx=4)
danger_hp_var = ctk.IntVar(value=danger_hp_threshold)
danger_hp_sld = ctk.CTkSlider(frame_dangerhp, from_=5, to=50, variable=danger_hp_var, width=70, height=18, corner_radius=9, fg_color="#21262d", button_color="#10b981", button_hover_color="#34d399", progress_color="#ef4444")
danger_hp_sld.pack(side='left', padx=2)
danger_hp_lbl = ctk.CTkLabel(frame_dangerhp, text=f"{danger_hp_threshold}%", text_color="#ef4444", font=('Malgun Gothic', 10, 'bold'), width=28)
danger_hp_lbl.pack(side='left')
def update_danger_hp_thr(*a):
    global danger_hp_threshold
    danger_hp_threshold = danger_hp_var.get(); danger_hp_lbl.configure(text=f"{danger_hp_threshold}%")
    save_hidden_config(loaded_pwd)
danger_hp_var.trace_add("write", update_danger_hp_thr)

frame_strong = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_strong.pack(pady=1, padx=2, fill="x")
chk_strong_heal = ctk.BooleanVar(value=True)
RoundedToggle(frame_strong, "⚡ 상위힐", "#58a6ff", var=chk_strong_heal).pack(side="left", padx=4)
sv = ctk.IntVar(value=strong_heal_pct)
ctk.CTkSlider(frame_strong, from_=5, to=50, variable=sv, width=60, height=18, fg_color="#21262d", button_color="#10b981", button_hover_color="#34d399", progress_color="#f38ba8").pack(side="left", padx=2)
s_lbl = ctk.CTkLabel(frame_strong, text=f"{strong_heal_pct}%", text_color="#f38ba8", font=("Malgun Gothic",10,"bold"), width=28)
s_lbl.pack(side="left")
def update_strong_thr(v, lbl=s_lbl):
    global strong_heal_pct
    strong_heal_pct = sv.get(); lbl.configure(text=f"{strong_heal_pct}%")
    save_hidden_config(loaded_pwd if loaded_pwd else "")

sv.trace_add("write", lambda *a: update_strong_thr(sv, s_lbl))

frame_atkhp = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_atkhp.pack(pady=1, padx=2, fill='x')
chk_attacker_sw = ctk.BooleanVar(value=True)
RoundedToggle(frame_atkhp, "⚔️ 격수", "#58a6ff", var=chk_attacker_sw, cmd=lambda: log_event(f"⚔️ 격수 {'ON' if chk_attacker_sw.get() else 'OFF'}")).pack(side='left', padx=4)
atkhp_var = ctk.IntVar(value=int(attacker_hp_threshold))
atkhp_sld = ctk.CTkSlider(frame_atkhp, from_=10, to=99, variable=atkhp_var, width=70, height=18, corner_radius=9, fg_color="#21262d", button_color="#10b981", button_hover_color="#34d399", progress_color="#ef4444")
atkhp_sld.pack(side='left', padx=2)
atkhp_lbl = ctk.CTkLabel(frame_atkhp, text=f"{int(attacker_hp_threshold)}%", text_color="#ef4444", font=('Malgun Gothic', 10, 'bold'), width=28)
atkhp_lbl.pack(side='left')
def update_atkhp_thr(*a):
    global attacker_hp_threshold
    attacker_hp_threshold = atkhp_var.get(); atkhp_lbl.configure(text=f"{int(attacker_hp_threshold)}%")
    save_hidden_config(loaded_pwd)
atkhp_var.trace_add("write", update_atkhp_thr)

# 마나 물약 (맨 밑)
chk_mna = ctk.BooleanVar(value=False)
frame_mna = ctk.CTkFrame(heal_body, fg_color="transparent")
frame_mna.pack(pady=1, padx=2, fill='x')
RoundedToggle(frame_mna, "💙 엠약", "#58a6ff", var=chk_mna, cmd=lambda: log_event(f"💙 엠약 {'ON' if chk_mna.get() else 'OFF'}")).pack(side='left', padx=4)
mna_var = ctk.IntVar(value=mna_threshold)
mna_sld = ctk.CTkSlider(frame_mna, from_=10, to=80, variable=mna_var, width=70, height=18, corner_radius=9, fg_color="#21262d", button_color="#10b981", button_hover_color="#34d399", progress_color="#89b4fa")
mna_sld.pack(side='left', padx=2)
mna_lbl = ctk.CTkLabel(frame_mna, text=f"{mna_threshold}%", text_color="#89b4fa", font=('Malgun Gothic', 10, 'bold'), width=28)
mna_lbl.pack(side='left')
def update_mna_thr(*a):
    global mna_threshold
    mna_threshold = mna_var.get(); mna_lbl.configure(text=f"{mna_threshold}%")
    if loaded_pwd: save_hidden_config(loaded_pwd)
mna_var.trace_add("write", update_mna_thr)



frame_timer_mini = ctk.CTkFrame(root, fg_color="#313244")
frame_timer_mini.pack(pady=1, padx=2, fill='x')
ctk.CTkLabel(frame_timer_mini, text="⏰ 예약종료:", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold')).pack(side="left", padx=4)
combo_timer = ctk.CTkComboBox(frame_timer_mini, values=["예약OFF", "1시간", "2시간", "3시간", "5시간", "10시간"], width=84, height=19, font=('Malgun Gothic', 10), command=set_shutdown_timer)
combo_timer.pack(side="right", padx=4, pady=2); combo_timer.set("예약OFF")

btn_frame = ctk.CTkFrame(root, fg_color="transparent")
btn_frame.pack(fill='x', padx=2, pady=1)
btn_frame.grid_columnconfigure(0, weight=1, uniform="btn"); btn_frame.grid_columnconfigure(1, weight=1, uniform="btn"); btn_frame.grid_columnconfigure(2, weight=1, uniform="btn") 
ctk.CTkButton(btn_frame, text="⚙️ 제어판", command=ask_admin_pw, fg_color="#800020", hover_color="#9e1a3a", border_width=1, border_color="#4a0010", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold'), height=26).grid(row=0, column=0)
ctk.CTkButton(btn_frame, text="📜 패치", command=open_patch_notes_panel, fg_color="#1f538d", hover_color="#14375e", border_width=1, border_color="#061220", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold'), height=26).grid(row=0, column=1)
ctk.CTkButton(btn_frame, text="📖 가이드", command=open_guide_panel, fg_color="#313244", hover_color="#45475a", border_width=1, border_color="#1a1b26", text_color="#ffffff", font=('Malgun Gothic', 10, 'bold'), height=26).grid(row=0, column=2)

lbl_auth = ctk.CTkLabel(root, text="", text_color="#89b4fa", font=('Malgun Gothic', 10, 'bold'), height=18)
lbl_auth.pack(pady=(2,0), ipady=0)
lbl_status = ctk.CTkLabel(root, text="💤 대기 중", text_color="#f38ba8", font=('Malgun Gothic', 13, 'bold'), height=22)
lbl_status.pack(pady=0, ipady=0)
frame_buff = ctk.CTkFrame(root, fg_color="#181825", corner_radius=5)
frame_buff.pack(pady=0, padx=2, fill='x')
lbl_buff = ctk.CTkLabel(frame_buff, text="✨ 버프 대기 ✨\n대기중", text_color="#6c7086", font=('Malgun Gothic', 11, 'bold'))
lbl_buff.pack(pady=0)
lbl_saved_coord = ctk.CTkLabel(root, text="", text_color="#a6e3a1", font=('Malgun Gothic', 10, 'bold'))

# UDP 모듈
chk_ontop = ctk.BooleanVar(value=False)
UDP_CONFIG_FILE = "udp_config.json"
udp_target_ip = "192.168.0.100"
if os.path.exists(UDP_CONFIG_FILE):
    try:
        with open(UDP_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        udp_target_ip = cfg.get("target_ip", udp_target_ip)
    except: pass

def save_udp_config():
    with open(UDP_CONFIG_FILE, "w", encoding="utf-8") as f: json.dump({"target_ip": udp_ip_var.get()}, f)

def get_my_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except: return "..."

frame_ontop_ctrl = ctk.CTkFrame(root, fg_color="#313244", corner_radius=6)
frame_ontop_ctrl.pack(pady=1, padx=2, fill='x')

row1 = ctk.CTkFrame(frame_ontop_ctrl, fg_color="transparent"); row1.pack(fill='x', padx=2, pady=(3,0))
ctk.CTkLabel(row1, text="📡", text_color="#f9e2af", font=('', 9)).pack(side='left')
udp_ip_var = ctk.StringVar(value=udp_target_ip)
udp_ip_entry = ctk.CTkEntry(row1, textvariable=udp_ip_var, width=95, height=22, fg_color="#1e1e2e", text_color="#cdd6f4", font=('Consolas', 9))
udp_ip_entry.pack(side='left', padx=2)
ctk.CTkButton(row1, text="저장", width=32, height=22, fg_color="#800020", hover_color="#9e1a3a", font=('Malgun Gothic', 8, 'bold'), command=save_udp_config).pack(side='left', padx=1)
udp_hp_lbl = ctk.CTkLabel(row1, text="HP: --", text_color="#ef4444", font=('Malgun Gothic', 10, 'bold'))
udp_hp_lbl.pack(side='right', padx=1)

row2 = ctk.CTkFrame(frame_ontop_ctrl, fg_color="transparent"); row2.pack(fill='x', padx=2, pady=(0,3))
lbl_my_ip = ctk.CTkLabel(row2, text=f"내IP:{get_my_ip()}", text_color="#cdd6f4", font=('Consolas', 8))
lbl_my_ip.pack(side='left', padx=4)
def toggle_ontop():
    if chk_ontop.get():
        frame_ontop_view.pack(pady=2, padx=2, fill='x')
    else:
        frame_ontop_view.pack_forget()
    auto_resize_height()

ctk.CTkSwitch(frame_ontop_ctrl, text="👁️ 격수 모니터", text_color="#ffffff", variable=chk_ontop, command=toggle_ontop, font=('Malgun Gothic', 11, 'bold'), switch_width=28, switch_height=14, progress_color="#a371f7", button_color="#ffffff", button_hover_color="#9e1a3a").pack(side="right", padx=10, pady=2)
lbl_ontop_status = ctk.CTkLabel(frame_ontop_ctrl, text="○ 대기중", text_color="#6c7086", font=('Malgun Gothic', 10, 'bold'))
lbl_ontop_status.pack(side="right", padx=10)

frame_ontop_view = tk.Frame(root, bg="#181825", height=30)
canvas_hp = tk.Canvas(frame_ontop_view, bg="#181825", height=30, highlightthickness=0)
canvas_hp.pack(fill="both", expand=True, padx=4, pady=3)

def draw_attacker_hp_bar():
    try:
        if canvas_hp and canvas_hp.winfo_exists():
            canvas_hp.delete("all")
            w = canvas_hp.winfo_width() or 225; h = canvas_hp.winfo_height() or 24
            hp_pct = max(0, min(100, attacker_hp_udp))
            fill_w = max(1, int(w * hp_pct / 100))
            canvas_hp.create_rectangle(0, 0, w, h, fill="#0d0f14", outline="#262a33", width=1)
            canvas_hp.create_rectangle(1, 1, fill_w, h-1, fill="#ef4444", outline="")
            canvas_hp.create_text(w//2, h//2, text=f"격수 HP: {hp_pct:.0f}%", fill="#f3f4f6", font=("Malgun Gothic", 10, "bold"))
    except: pass

def update_udp_hp_label():
    try:
        if root and root.winfo_exists():
            if last_udp_time == 0 or time.time() - last_udp_time > 2.0:
                udp_hp_lbl.configure(text="HP: 수신안됨", text_color="#ef4444")
                lbl_ontop_status.configure(text="○ 연결안됨", text_color="#f38ba8")
            else:
                udp_hp_lbl.configure(text=f"HP: {attacker_hp_udp:.0f}%", text_color="#ef4444")
                lbl_ontop_status.configure(text="✅ 수신중", text_color="#a6e3a1")
            draw_attacker_hp_bar()
            root.after(300, update_udp_hp_label)
    except: pass

# UDP 원격 명령 매핑
UDP_CMD_MAP = {
    b'I': 'on_main_toggle',    # Insert → 시작/종료
    b'H': 'on_caps_lock',      # Home   → 따라다니기 토글
    b'P': 'on_tab_toggle',     # PgUp   → 고정 토글
    b'L': 'on_f4_toggle',      # F4     → 줍기 토글
}
# Alt+숫자 → F3→F키→F1 매크로 (슬롯 1~8 → F5~F12)
UDP_SLOT_KEYS = {1: '5', 2: '6', 3: '7', 4: '8', 5: '9', 6: 'X', 7: 'Y', 8: 'Z'}  # F5~F12
def udp_macro_slot(n):
    """Alt+숫자 매크로: 고정해제→F3→F키→F1→고정복구 (클릭유지)"""
    global ser, running
    if not running or not ser or not ser.is_open: return
    try:
        key = UDP_SLOT_KEYS.get(n, '5')
        time.sleep(0.02)
        is_fixed = chk_fix.get() if chk_fix else False
        if is_fixed: ser.write(b'R'); time.sleep(0.10)
        ser.write(b'3'); time.sleep(random.uniform(0.30, 0.45))
        ser.write(key.encode()); time.sleep(0.15)
        ser.write(b'K'); time.sleep(0.10)
        ser.write(b'1'); time.sleep(random.uniform(0.25, 0.40))
        if is_fixed: ser.write(b'H'); time.sleep(0.05)
    except: pass
def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_ATTACKER_PORT))
    sock.settimeout(1.0)
    global attacker_hp_udp, attacker_poisoned, attacker_petrified, last_udp_time
    while timer_thread_active:
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) == 1:
                if data in UDP_CMD_MAP:
                    func_name = UDP_CMD_MAP[data]
                    f = globals().get(func_name)
                    if f: root.after(0, f)
                elif data in (b'1',b'2',b'3',b'4',b'5',b'6',b'7',b'8'):
                    n = int(data.decode())
                    root.after(0, lambda s=n: udp_macro_slot(s))
            elif len(data) == 4:
                attacker_hp_udp = struct.unpack('f', data)[0]; last_udp_time = time.time()
            elif len(data) == 5:
                attacker_hp_udp, poison_byte = struct.unpack('fB', data)
                attacker_poisoned = bool(poison_byte); last_udp_time = time.time()
            elif len(data) == 6:
                attacker_hp_udp, poison_byte, petrify_byte = struct.unpack('fBB', data)
                attacker_poisoned = bool(poison_byte); attacker_petrified = bool(petrify_byte); last_udp_time = time.time()
        except socket.timeout: continue
        except: break
    sock.close()

is_gui_hidden = False
def toggle_gui(e=None):
    global is_gui_hidden
    if is_gui_hidden: root.deiconify(); is_gui_hidden = False
    else: root.withdraw(); is_gui_hidden = True

keyboard.on_release_key('delete', toggle_gui) 
keyboard.on_release_key('space', on_space_save) 
keyboard.on_release_key('home', on_caps_lock)
keyboard.on_release_key('page up', on_tab_toggle)
keyboard.on_release_key('insert', on_main_toggle)
keyboard.on_release_key('f4', on_f4_toggle)

timer_thread_active = True
Thread(target=reserve_shutdown_worker, daemon=True).start()
Thread(target=expert_logic, daemon=True).start()
Thread(target=lcd_logo_worker, daemon=True).start()
Thread(target=update_ui_timer, daemon=True).start()
Thread(target=udp_listener, daemon=True).start()
update_udp_hp_label()

lbl_log = ctk.CTkTextbox(root, height=55, fg_color="#0d1117", text_color="#a6e3a1",
                          font=("Consolas", 9), border_width=1, border_color="#262a33",
                          corner_radius=6, activate_scrollbars=False)
lbl_log.pack(fill="x", padx=6, pady=(4,2))
lbl_log.insert("1.0", "🟢 시스템 시작")
lbl_log.configure(state="disabled")
root.mainloop()