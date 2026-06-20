# -*- coding: utf-8 -*-
"""아지트 버프봇 — 채팅 OCR 감지 → 시전키 출력"""

import sys, subprocess, time, os

for mod, pkg in [("numpy","numpy"),("PIL","pillow"),("mss","mss"),
                  ("serial","pyserial"),("pytesseract","pytesseract")]:
    try:
        __import__(mod)
    except:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

import numpy as np
import mss
import tkinter as tk
import threading
from datetime import datetime
from PIL import Image

# ─── 설정 ────────────────────────────────
CHAT_ROI = (10, 800, 350, 40)       # left,top,width,height
SCAN_INTERVAL = 0.5
COOLDOWN = 8
FULL_KW = ["!풀버프", "풀버프"]
BASIC_KW = ["!버프", "버프"]
KEYWORDS = FULL_KW + BASIC_KW        # ← 빠졌던 거!
FKEY_MAP = {5:'5',6:'6',7:'7',8:'8',9:'9',10:'X',11:'Y',12:'Z'}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Tesseract 자동설치 ────────────────────
_tess_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
]
TESS_CMD = None
for tp in _tess_paths:
    if os.path.exists(tp):
        TESS_CMD = tp
        break
if not TESS_CMD:
    try:
        import urllib.request
        url = ("https://github.com/UB-Mannheim/tesseract/releases/download/"
               "v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe")
        installer = os.path.join(os.environ["TEMP"], "tesseract_install.exe")
        urllib.request.urlretrieve(url, installer)
        subprocess.run([installer, "/S"], timeout=120)
        os.remove(installer)
        for tp in _tess_paths:
            if os.path.exists(tp):
                TESS_CMD = tp
                break
        if TESS_CMD:
            try:
                tessdata = os.path.join(os.path.dirname(TESS_CMD), "tessdata")
                kor_path = os.path.join(tessdata, "kor.traineddata")
                if not os.path.exists(kor_path):
                    kor_url = ("https://github.com/tesseract-ocr/tessdata/raw/main/"
                               "kor.traineddata")
                    urllib.request.urlretrieve(kor_url, kor_path)
            except:
                pass
    except:
        pass

# ─── OCR 초기화 ──────────────────────────
OCR_OK = False
try:
    import pytesseract
    if TESS_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESS_CMD
    _test = pytesseract.image_to_string(Image.new("RGB", (10, 10)))
    OCR_OK = True
except:
    pass


def ocr_text(img_array):
    """OCR로 이미지에서 텍스트 추출"""
    try:
        img = Image.fromarray(img_array)
        text = pytesseract.image_to_string(img, lang="kor+eng", config="--psm 7")
        return text.strip()
    except:
        return ""


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(os.path.join(SCRIPT_DIR, "buffbot.log"), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


# ─── ROI 선택 오버레이 ────────────────────
def open_roi_overlay(btn_roi_entry, roi_var):
    ov = tk.Toplevel(root)
    ov.attributes("-fullscreen", True)
    ov.attributes("-alpha", 0.35)
    ov.configure(bg="black")
    ov.attributes("-topmost", True)
    ov.focus_force()
    cv = tk.Canvas(ov, bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)
    d = {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "r": None}

    def dn(e):
        d["x1"], d["y1"] = e.x_root, e.y_root
        d["r"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#10b981", width=4)

    def mv(e):
        if d["r"]:
            cv.coords(d["r"], d["x1"] - ov.winfo_rootx(), d["y1"] - ov.winfo_rooty(), e.x, e.y)

    def up(e):
        d["x2"], d["y2"] = e.x_root, e.y_root
        x1 = min(d["x1"], d["x2"])
        y1 = min(d["y1"], d["y2"])
        x2 = max(d["x1"], d["x2"])
        y2 = max(d["y1"], d["y2"])
        ov.destroy()
        if x2 - x1 < 20 or y2 - y1 < 8:
            return
        roi_var.set(f"{x1},{y1},{x2-x1},{y2-y1}")

    cv.bind("<ButtonPress-1>", dn)
    cv.bind("<B1-Motion>", mv)
    cv.bind("<ButtonRelease-1>", up)

    tk.Label(ov, text="📐 채팅창 영역 드래그", fg="#10b981",
             bg="black", font=("Malgun Gothic", 13, "bold")).place(relx=0.5, rely=0.02, anchor="n")
    tk.Label(ov, text="ESC=취소", fg="#6c7086",
             bg="black", font=("", 9)).place(relx=0.5, rely=0.06, anchor="n")
    ov.bind("<Escape>", lambda e: ov.destroy())


# ─── GUI ──────────────────────────────────
DG = "#0d0f14"
FG = "#1e1e2e"
TX = "#cdd6f4"
AC = "#10b981"
YL = "#f9e2af"
GR = "#6c7086"
RD = "#ef4444"

root = tk.Tk()
root.title("아지트 버프봇")
root.geometry("280x360+0+0")
root.attributes("-topmost", True)
root.configure(bg=DG)

tk.Label(root, text="🔮 아지트 버프봇", bg=DG, fg=YL,
         font=("Malgun Gothic", 12, "bold")).pack(pady=(10, 4))

# ── ROI 영역 ──
fr_roi = tk.Frame(root, bg=DG)
fr_roi.pack(fill='x', padx=10, pady=3)
tk.Label(fr_roi, text="📐 채팅 ROI", bg=DG, fg=GR,
         font=("Malgun Gothic", 8)).pack(side='left')
roi_var = tk.StringVar(value=f"{CHAT_ROI[0]},{CHAT_ROI[1]},{CHAT_ROI[2]},{CHAT_ROI[3]}")
e_roi = tk.Entry(fr_roi, textvariable=roi_var, width=18, bg=FG, fg=TX,
                 font=("Consolas", 9), relief='flat', insertbackground=TX)
e_roi.pack(side='left', padx=3)
tk.Button(fr_roi, text="🖱️", bg=FG, fg=AC, font=("", 8),
          relief='flat', cursor="hand2",
          command=lambda: open_roi_overlay(e_roi, roi_var)).pack(side='left')

# ── 버프 체크박스 ──
tk.Label(root, text="✨ !풀버프 시전 목록", bg=DG, fg=YL,
         font=("Malgun Gothic", 9, "bold")).pack(pady=(8, 2))
chk_full = {}
for row in range(2):
    f = tk.Frame(root, bg=DG)
    f.pack(fill='x', padx=10, pady=1)
    for col in range(4):
        n = row * 4 + col + 5
        v = tk.BooleanVar(value=True)
        chk_full[n] = v
        tk.Checkbutton(f, text=f"F{n}", variable=v, bg=DG, fg=YL,
                       font=("Consolas", 9, "bold"),
                       selectcolor=DG, activebackground=DG,
                       activeforeground=AC).pack(side='left', padx=3)

tk.Label(root, text="✨ !버프 시전 목록", bg=DG, fg="#a6e3a1",
         font=("Malgun Gothic", 9, "bold")).pack(pady=(6, 2))
chk_basic = {}
for row in range(2):
    f = tk.Frame(root, bg=DG)
    f.pack(fill='x', padx=10, pady=1)
    for col in range(4):
        n = row * 4 + col + 5
        v = tk.BooleanVar(value=(n <= 8))
        chk_basic[n] = v
        tk.Checkbutton(f, text=f"F{n}", variable=v, bg=DG, fg="#a6e3a1",
                       font=("Consolas", 9, "bold"),
                       selectcolor=DG, activebackground=DG,
                       activeforeground=AC).pack(side='left', padx=3)

# ── 상태 + 시작 ──
lbl_detect = tk.Label(root, text="", bg=DG, fg=YL,
                      font=("Malgun Gothic", 9), height=1)
lbl_detect.pack(pady=(8, 0))
lbl_status = tk.Label(root, text="⏸ 준비", bg=DG, fg=GR,
                      font=("Malgun Gothic", 10, "bold"))
lbl_status.pack(pady=(6, 4))

running = False
arduino_connected = False      # ← 아두이노 연결 여부 플래그


def start_bot():
    global running, CHAT_ROI, arduino_connected
    # ROI 파싱
    try:
        p = [int(x.strip()) for x in roi_var.get().split(",")]
        if len(p) == 4:
            CHAT_ROI = tuple(p)
    except:
        pass

    # 아두이노 연결 시도 (실패해도 계속)
    arduino_connected = False
    try:
        import serial
        from serial.tools.list_ports import comports
        port = None
        for p in comports():
            if "Arduino" in p.description or "CH340" in p.description or "USB" in p.description:
                port = p.device
                break
        if not port:
            ports = [p.device for p in comports()]
            port = ports[0] if ports else "COM3"
        _ser = serial.Serial(port, 9600, timeout=0)
        arduino_connected = True
        log(f"✅ 아두이노 연결: {port}")
        lbl_status.config(text="🟢 연결 + 감시중", fg=AC)
    except Exception as e:
        log(f"⚠️ 아두이노 없음 (OCR 감지만): {e}")
        lbl_status.config(text="🟡 감시중 (OCR only)", fg="#fbbf24")

    running = True
    threading.Thread(target=buff_loop, daemon=True).start()


def buff_loop():
    global running, arduino_connected

    # ── baseline 초기화 ──
    sct = mss.MSS()
    baseline = None
    try:
        raw = sct.grab(CHAT_ROI)
        baseline = np.array(raw, dtype=np.uint8)[:, :, :3]
    except:
        pass

    last_buff_time = 0

    while running:
        try:
            time.sleep(SCAN_INTERVAL)
            if time.time() - last_buff_time < COOLDOWN:
                continue

            # 화면 캡처
            try:
                raw = sct.grab(CHAT_ROI)
                current = np.array(raw, dtype=np.uint8)[:, :, :3]
            except:
                continue

            detected = False
            text = ""
            typ = ""  # ← typ 초기화!

            # ── OCR 감지 ──
            if OCR_OK:
                text = ocr_text(current)
                if text:
                    # 키워드 매칭
                    for kw in FULL_KW:
                        if kw in text:
                            detected = True
                            typ = "!풀버프"
                            break
                    if not detected:
                        for kw in BASIC_KW:
                            if kw in text:
                                detected = True
                                typ = "!버프"
                                break

            # ── OCR 불가면 픽셀 변화 감지 ──
            if not detected and baseline is not None:
                diff = np.abs(baseline.astype(int) - current.astype(int))
                change = np.sum(diff > 30) / (diff.shape[0] * diff.shape[1])
                if change > 0.02:
                    detected = True
                    typ = "!풀버프"  # 픽셀변화면 무조건 풀버프로

            if detected:
                # 감지 로그
                log(f"✅ {typ} 감지! text='{text}'")
                lbl_detect.config(text=f"✅ {typ}")
                lbl_status.config(text=f"🔮 {typ} 감지!", fg="#fbbf24")

                # ── 아두이노 있으면 키 전송 ──
                if arduino_connected:
                    try:
                        import serial
                        from serial.tools.list_ports import comports
                        for p in comports():
                            if "Arduino" in p.description or "CH340" in p.description or "USB" in p.description:
                                s = serial.Serial(p.device, 9600, timeout=0)
                                break
                        else:
                            s = None
                        if s:
                            is_full = (typ == "!풀버프")
                            chk = chk_full if is_full else chk_basic
                            for n in range(5, 13):
                                if not running:
                                    break
                                if chk[n].get():
                                    s.write(FKEY_MAP[n].encode())
                                    time.sleep(0.2)
                            s.close()
                            log(f"📤 {typ} 키전송 완료")
                    except Exception as e:
                        log(f"⚠️ 키전송 실패: {e}")
                        arduino_connected = False
                else:
                    # 아두이노 없으면 알림만
                    log(f"📋 아두이노 없음 - 감지만: {typ}")
                    lbl_detect.config(text=f"✅ {typ} (키전송X)")

                last_buff_time = time.time()
                time.sleep(0.5)
                lbl_status.config(text="🟡 감시중 (OCR only)" if not arduino_connected else "🟢 감시중")

        except Exception as e:
            log(f"루프 오류: {e}")


def on_close():
    global running
    running = False
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

tk.Button(root, text="▶ 시작", bg=AC, fg="#000",
          font=("Malgun Gothic", 10, "bold"),
          relief='flat', cursor="hand2", padx=20, pady=3,
          command=start_bot).pack(pady=4)

root.mainloop()
try:
    os.remove(os.path.abspath(__file__))
except:
    pass
