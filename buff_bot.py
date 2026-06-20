# -*- coding: utf-8 -*-
"""아지트 버프봇 — 채팅 감지 → 체크된 버프만 순차시전"""
import sys, subprocess, time, os, glob
for mod, pkg in [("numpy","numpy"),("PIL","pillow"),("mss","mss"),("serial","pyserial"),("serial.tools","pyserial"),("pytesseract","pytesseract")]:
    try: __import__(mod)
    except: subprocess.check_call([sys.executable,"-m","pip","install",pkg,"--quiet"])

import numpy as np, mss, serial, tkinter as tk, threading, ctypes
from serial.tools.list_ports import comports
from datetime import datetime
from PIL import Image

CHAT_ROI = (10, 800, 350, 40)
BAUD_RATE = 9600
SCAN_INTERVAL = 0.5
COOLDOWN = 8
FULL_KW = ["!풀버프", "풀버프"]
BASIC_KW = ["!버프", "버프"]

FKEY_MAP = {5:'5',6:'6',7:'7',8:'8',9:'9',10:'X',11:'Y',12:'Z'}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# Tesseract 자동설치
_tess_paths = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]
TESS_CMD = None
for tp in _tess_paths:
    if os.path.exists(tp): TESS_CMD = tp; break
if not TESS_CMD:
    try:
        import urllib.request
        url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
        installer = os.path.join(os.environ["TEMP"], "tesseract_install.exe")
        urllib.request.urlretrieve(url, installer)
        subprocess.run([installer, "/S"], timeout=120)
        os.remove(installer)
        for tp in _tess_paths:
            if os.path.exists(tp): TESS_CMD = tp; break
    except: pass

# OCR 초기화
OCR_OK = False
try:
    import pytesseract
    # Tesseract 기본 경로
    if TESS_CMD: pytesseract.pytesseract.tesseract_cmd = TESS_CMD
    _test = pytesseract.image_to_string(Image.new("RGB",(10,10)))
    OCR_OK = True
except: pass

def ocr_text(img_array):
    """OCR로 이미지에서 텍스트 추출 (실패 시 빈 문자열)"""
    try:
        img = Image.fromarray(img_array)
        text = pytesseract.image_to_string(img, lang="kor+eng", config="--psm 7")
        return text.strip()
    except: return ""

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(os.path.join(SCRIPT_DIR,"buffbot.log"),"a",encoding="utf-8") as f: f.write(f"[{ts}] {msg}\n")

def find_arduino():
    for p in comports():
        if "Arduino" in p.description or "CH340" in p.description or "USB" in p.description:
            return p.device
    ports = [p.device for p in comports()]
    return ports[0] if ports else "COM3"

def connect_arduino(port):
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=0)
        log(f"연결: {port}")
        return ser
    except:
        log(f"연결실패: {port}")
        return None

# ROI 드래그 오버레이
def open_roi_overlay():
    ov = tk.Toplevel(root); ov.attributes("-fullscreen",True); ov.attributes("-alpha",0.35)
    ov.configure(bg="black"); ov.attributes("-topmost",True); ov.focus_force()
    cv = tk.Canvas(ov,bg="black",highlightthickness=0); cv.pack(fill="both",expand=True)
    d = {"x1":0,"y1":0,"x2":0,"y2":0,"r":None}
    def dn(e): d["x1"],d["y1"]=e.x_root,e.y_root; d["r"]=cv.create_rectangle(e.x,e.y,e.x,e.y,outline=AC,width=4)
    def mv(e):
        if d["r"]: cv.coords(d["r"],d["x1"]-ov.winfo_rootx(),d["y1"]-ov.winfo_rooty(),e.x,e.y)
    def up(e):
        d["x2"],d["y2"]=e.x_root,e.y_root
        x1=min(d["x1"],d["x2"]);y1=min(d["y1"],d["y2"]);x2=max(d["x1"],d["x2"]);y2=max(d["y1"],d["y2"])
        ov.destroy()
        if x2-x1<20 or y2-y1<8: return
        roi_var.set(f"{x1},{y1},{x2},{y2}")
    cv.bind("<ButtonPress-1>",dn); cv.bind("<B1-Motion>",mv); cv.bind("<ButtonRelease-1>",up)
    tk.Label(ov,text="📐 채팅창 영역 드래그",fg=AC,bg="black",font=("Malgun Gothic",13,"bold")).place(relx=0.5,rely=0.02,anchor="n")
    tk.Label(ov,text="ESC=취소",fg=GR,bg="black",font=("",9)).place(relx=0.5,rely=0.06,anchor="n")
    ov.bind("<Escape>",lambda e:ov.destroy())

# ─── GUI ──────────────────────────
DG = "#0d0f14"; FG = "#1e1e2e"; TX = "#cdd6f4"; AC = "#10b981"; YL = "#f9e2af"; GR = "#6c7086"

root = tk.Tk()
root.title("아지트 버프봇")
root.geometry("270x350+0+0")
root.attributes("-topmost", True)
root.configure(bg=DG)

# 타이틀
tk.Label(root, text="🔮 아지트 버프봇", bg=DG, fg=YL, font=("Malgun Gothic",12,"bold")).pack(pady=(10,4))

# COM 포트
f1 = tk.Frame(root, bg=DG); f1.pack(fill='x', padx=10, pady=2)
tk.Label(f1, text="📡", bg=DG, fg=TX, font=("",9)).pack(side='left')
port_var = tk.StringVar(value=find_arduino())
tk.Entry(f1, textvariable=port_var, width=8, bg=FG, fg=TX, font=("Consolas",10),
         justify='center', relief='flat', insertbackground=TX).pack(side='left', padx=4)
tk.Button(f1, text="🔄", bg=FG, fg=TX, font=("",7), relief='flat', cursor="hand2",
          command=lambda: port_var.set(find_arduino())).pack(side='left')

# ROI
f2 = tk.Frame(root, bg=DG); f2.pack(fill='x', padx=10, pady=2)
tk.Label(f2, text="📐 채팅영역", bg=DG, fg=GR, font=("Malgun Gothic",8)).pack(side='left')
roi_var = tk.StringVar(value=f"{CHAT_ROI[0]},{CHAT_ROI[1]},{CHAT_ROI[2]},{CHAT_ROI[3]}")
tk.Entry(f2, textvariable=roi_var, width=15, bg=FG, fg=TX, font=("Consolas",9),
         relief='flat', insertbackground=TX).pack(side='left', padx=3)
tk.Button(f2, text="🖱️", bg=FG, fg=AC, font=("",8), relief='flat', cursor="hand2",
          command=open_roi_overlay).pack(side='left')
# COM포트 설명
tk.Label(root, text="📡 자동감지 🔄 수동탐색", bg=DG, fg=GR, font=("Malgun Gothic",7)).pack()

# 버프 체크박스
tk.Label(root, text="✨ 시전할 버프", bg=DG, fg=YL, font=("Malgun Gothic",9,"bold")).pack(pady=(10,3))
chk_vars = {}
for row in range(2):
    f = tk.Frame(root, bg=DG); f.pack(fill='x', padx=10, pady=1)
    for col in range(4):
        n = row*4+col+5
        v = tk.BooleanVar(value=True)
        chk_vars[n] = v
        tk.Checkbutton(f, text=f"F{n}", variable=v, bg=DG, fg=TX, font=("Consolas",9,"bold"),
            selectcolor=DG, activebackground=DG, activeforeground=AC).pack(side='left', padx=3)

# 상태 + 시작
lbl_detect = tk.Label(root, text="", bg=DG, fg=YL, font=("Malgun Gothic",9), height=1)
lbl_detect.pack(pady=(6,0))
lbl_status = tk.Label(root, text="⏸ 준비", bg=DG, fg=GR, font=("Malgun Gothic",10,"bold"))
lbl_status.pack(pady=(10,4))

tk.Button(root, text="▶ 시작", bg=AC, fg="#000", font=("Malgun Gothic",10,"bold"),
          relief='flat', cursor="hand2", padx=20, pady=3,
          command=lambda: start_bot()).pack(pady=2)

ser = None; running = False

def start_bot():
    global ser, running, CHAT_ROI
    try:
        p = [int(x.strip()) for x in roi_var.get().split(",")]
        CHAT_ROI = (p[0], p[1], p[2], p[3])
    except: pass
    ser = connect_arduino(port_var.get())
    if not ser:
        lbl_status.config(text="❌ 연결실패", fg="#ef4444"); return
    running = True; lbl_status.config(text="🟢 감시중", fg=AC)
    threading.Thread(target=buff_loop, daemon=True).start()

def buff_loop():
    global running
    sct = mss.MSS(); last_buff_time = 0
    roi = {"left": CHAT_ROI[0], "top": CHAT_ROI[1], "width": max(CHAT_ROI[2]-CHAT_ROI[0],1), "height": max(CHAT_ROI[3]-CHAT_ROI[1],1)}
    while running:
        try:
            time.sleep(SCAN_INTERVAL)
            if time.time()-last_buff_time < COOLDOWN: continue
            img = sct.grab(roi); current = np.array(img, dtype=np.uint8)[:,:,:3]
            # OCR 키워드 감지
            detected = False
            if OCR_OK:
                text = ocr_text(current)
                detected = any(kw in text for kw in KEYWORDS)
            else:
                # OCR 없으면 픽셀변화 감지 (fallback)
                diff = np.abs(baseline.astype(int)-current.astype(int))
                detected = np.sum(diff>30)/(diff.shape[0]*diff.shape[1]) > 0.02
            if detected:
                is_full = any(kw in text for kw in FULL_KW) if OCR_OK else True
                typ = "!풀버프" if is_full else "!버프"
                log(f"📩 {typ} 감지!")
                root.after(0, lambda t=typ: lbl_status.config(text=f"🔮 {t} 감지!", fg="#fbbf24"))
                root.after(0, lambda t=typ: lbl_detect.config(text=f"✅ {t}"))
                # 둘 다 체크된 F5~F12 사용
                for n in range(5,13):
                    if not running: break
                    if chk_vars[n].get():
                        ser.write(FKEY_MAP[n].encode()); time.sleep(0.2)
                root.after(0, lambda: lbl_status.config(text="🟢 감시중", fg=AC))
                last_buff_time = time.time()
        except Exception as e: log(f"오류: {e}")

def on_close():
    global running; running = False
    if ser: ser.close()
    root.destroy()
root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
try: os.remove(os.path.abspath(__file__))
except: pass
