# -*- coding: utf-8 -*-
"""아지트 버프봇 — 채팅 OCR 감지 → 시전키 출력
개선판: OCR 디버그, ROI 시각화, 테스트 버튼, Tesseract 진단 로그 포함
"""

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
        import ssl
        # SSL 인증서 우회 (Windows 환경)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = ("https://github.com/UB-Mannheim/tesseract/releases/download/"
               "v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe")
        installer = os.path.join(os.environ["TEMP"], "tesseract_install.exe")
        with urllib.request.urlopen(url, timeout=30, context=ctx) as resp:
            with open(installer, "wb") as f:
                f.write(resp.read())
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
                    with urllib.request.urlopen(kor_url, timeout=30, context=ctx) as kr:
                        with open(kor_path, "wb") as kf:
                            kf.write(kr.read())
            except:
                pass
    except:
        pass

# ─── OCR 초기화 및 진단 ──────────────────
OCR_OK = False
OCR_DIAG = []  # 진단 메시지 저장 (GUI에 표시)

def diagnose_tesseract():
    """Tesseract 설치 상태를 진단하고 로그에 기록"""
    global OCR_OK
    diag = []
    
    # 1. Tesseract 실행 파일 확인
    if TESS_CMD:
        diag.append(f"✅ Tesseract 실행파일: {TESS_CMD}")
    else:
        diag.append("❌ Tesseract 실행파일을 찾을 수 없음")
        diag.append("   C:\\Program Files\\Tesseract-OCR\\tesseract.exe 확인")
        return diag
    
    # 2. Tesseract 버전 확인
    try:
        ver = subprocess.run([TESS_CMD, "--version"], capture_output=True, text=True, timeout=5)
        first_line = ver.stdout.split('\n')[0] if ver.stdout else ver.stderr.split('\n')[0]
        diag.append(f"📌 Tesseract 버전: {first_line.strip()}")
    except Exception as e:
        diag.append(f"⚠️ 버전 확인 실패: {e}")
    
    # 3. tessdata 디렉토리 확인
    tessdata_dir = os.path.join(os.path.dirname(TESS_CMD), "tessdata")
    if os.path.exists(tessdata_dir):
        files = [f for f in os.listdir(tessdata_dir) if f.endswith(".traineddata")]
        diag.append(f"📁 tessdata: {len(files)}개 언어팩")
        if "kor.traineddata" in files:
            diag.append("   ✅ 한국어팩(kor) 설치됨")
        else:
            diag.append("   ⚠️ 한국어팩(kor) 없음 → 한글 OCR 불량 가능")
        if "eng.traineddata" in files:
            diag.append("   ✅ 영어팩(eng) 설치됨")
    else:
        diag.append(f"⚠️ tessdata 디렉토리 없음: {tessdata_dir}")
    
    # 4. pytesseract 모듈 및 OCR 테스트
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESS_CMD
        
        # 테스트: 간단한 이미지로 OCR 수행
        test_img = Image.new("RGB", (50, 20), color=(255, 255, 255))
        # 흑백 테스트: 검은색 픽셀로 텍스트 흉내
        import PIL.ImageDraw
        draw = PIL.ImageDraw.Draw(test_img)
        draw.text((2, 2), "TEST", fill=(0, 0, 0))
        test_result = pytesseract.image_to_string(test_img, lang="kor+eng", config="--psm 7")
        diag.append(f"🔬 OCR 테스트 결과: '{test_result.strip()}'")
        OCR_OK = True
        diag.append("✅ OCR 초기화 성공!")
    except Exception as e:
        diag.append(f"❌ OCR 초기화 실패: {e}")
        OCR_OK = False
    
    return diag

# 진단 실행
OCR_DIAG = diagnose_tesseract()


def ocr_text(img_array):
    """OCR로 이미지에서 텍스트 추출 (개선: 이미지 전처리 + 디버그 로깅)"""
    try:
        img = Image.fromarray(img_array)
        # 전처리: 그레이스케일 → 대비 증가 → 선명하게
        img = img.convert("L")
        import PIL.ImageOps
        img = PIL.ImageOps.autocontrast(img, cutoff=5)
        img = img.point(lambda x: 0 if x < 40 else 255 if x > 200 else x)
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        text = pytesseract.image_to_string(img, lang="kor+eng", config="--psm 6 --oem 3")
        return text.strip()
    except Exception as e:
        log(f"⚠️ OCR 오류: {e}")
        return ""


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(os.path.join(SCRIPT_DIR, "buffbot.log"), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    # 화면에도 출력 (개선)
    print(f"[{ts}] {msg}")


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


# ─── ROI 시각화 오버레이 (개선: 화면에 파란 테두리) ───
roi_overlay_window = None

def show_roi_overlay(roi):
    """현재 ROI 영역을 화면에 파란색 테두리로 표시 (3초 후 자동 제거)"""
    global roi_overlay_window
    try:
        # 기존 오버레이 닫기
        hide_roi_overlay()
        
        x, y, w, h = roi
        ov = tk.Toplevel(root)
        ov.attributes("-fullscreen", True)
        ov.attributes("-transparentcolor", "#010101")
        ov.attributes("-topmost", True)
        ov.overrideredirect(True)
        ov.configure(bg="#010101")
        
        cv = tk.Canvas(ov, bg="#010101", highlightthickness=0)
        cv.pack(fill="both", expand=True)
        # 파란색 테두리 (두꺼운 실선)
        cv.create_rectangle(x, y, x+w, y+h, outline="#3b82f6", width=4, dash=(10, 5))
        cv.create_text(x + w//2, y + h + 20, text=f"📐 채팅 ROI ({x},{y} {w}x{h})",
                       fill="#3b82f6", font=("Malgun Gothic", 12, "bold"))
        
        roi_overlay_window = ov
        # 3초 후 자동 제거
        root.after(3000, hide_roi_overlay)
    except Exception as e:
        log(f"⚠️ ROI 오버레이 표시 오류: {e}")

def hide_roi_overlay():
    global roi_overlay_window
    if roi_overlay_window:
        try:
            roi_overlay_window.destroy()
        except:
            pass
        roi_overlay_window = None


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
root.geometry("340x520+0+0")
root.attributes("-topmost", True)
root.configure(bg=DG)

tk.Label(root, text="🔮 아지트 버프봇", bg=DG, fg=YL,
         font=("Malgun Gothic", 12, "bold")).pack(pady=(8, 2))

# ── Tesseract 진단 상태 표시 (개선) ──
diag_frame = tk.Frame(root, bg=FG, highlightbackground=GR, highlightthickness=1)
diag_frame.pack(fill='x', padx=8, pady=2)
diag_text_widget = tk.Text(diag_frame, height=4, bg=FG, fg=TX,
                            font=("Consolas", 8), relief='flat', wrap='word',
                            insertbackground=TX)
diag_text_widget.pack(fill='both', padx=4, pady=2)
diag_text_widget.insert('1.0', "\n".join(OCR_DIAG))
diag_text_widget.config(state='disabled')

# ── ROI 영역 ──
fr_roi = tk.Frame(root, bg=DG)
fr_roi.pack(fill='x', padx=10, pady=2)
tk.Label(fr_roi, text="📐 채팅 ROI", bg=DG, fg=GR,
         font=("Malgun Gothic", 8)).pack(side='left')
roi_var = tk.StringVar(value=f"{CHAT_ROI[0]},{CHAT_ROI[1]},{CHAT_ROI[2]},{CHAT_ROI[3]}")
e_roi = tk.Entry(fr_roi, textvariable=roi_var, width=18, bg=FG, fg=TX,
                 font=("Consolas", 9), relief='flat', insertbackground=TX)
e_roi.pack(side='left', padx=3)
tk.Button(fr_roi, text="🖱️", bg=FG, fg=AC, font=("", 8),
          relief='flat', cursor="hand2",
          command=lambda: open_roi_overlay(e_roi, roi_var)).pack(side='left')

# ── ROI 시각화 버튼 (개선) ──
tk.Button(fr_roi, text="👁️", bg=FG, fg="#3b82f6", font=("", 8),
          relief='flat', cursor="hand2",
          command=lambda: show_roi_overlay(tuple(int(x.strip()) for x in roi_var.get().split(",")) if len(roi_var.get().split(","))==4 else CHAT_ROI)
          ).pack(side='left', padx=1)

# ── OCR 실시간 인식 결과 표시 (개선) ──
tk.Label(root, text="📝 OCR 인식 결과", bg=DG, fg=GR,
         font=("Malgun Gothic", 8)).pack(pady=(4, 1))
lbl_ocr_result = tk.Label(root, text="(대기 중...)", bg=FG, fg=GR,
                           font=("Consolas", 9), anchor='w',
                           height=1, wraplength=320, justify='left')
lbl_ocr_result.pack(fill='x', padx=10, pady=1)

# ── 버프 체크박스 ──
tk.Label(root, text="✨ !풀버프 시전 목록", bg=DG, fg=YL,
         font=("Malgun Gothic", 9, "bold")).pack(pady=(5, 1))
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
         font=("Malgun Gothic", 9, "bold")).pack(pady=(4, 1))
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

# ── 상태 ──
lbl_detect = tk.Label(root, text="", bg=DG, fg=YL,
                      font=("Malgun Gothic", 9), height=1)
lbl_detect.pack(pady=(4, 0))
lbl_status = tk.Label(root, text="⏸ 준비", bg=DG, fg=GR,
                      font=("Malgun Gothic", 10, "bold"))
lbl_status.pack(pady=(2, 2))

# ── OCR 디버그 로그 (개선: 실시간 스크롤 로그) ──
tk.Label(root, text="📋 디버그 로그", bg=DG, fg=GR,
         font=("Malgun Gothic", 8)).pack()
log_frame = tk.Frame(root, bg=FG, highlightbackground=GR, highlightthickness=1)
log_frame.pack(fill='both', padx=8, pady=1, expand=True)
log_text = tk.Text(log_frame, height=5, bg=FG, fg=GR,
                    font=("Consolas", 8), relief='flat', wrap='word',
                    state='disabled', insertbackground=TX)
scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
log_text.configure(yscrollcommand=scrollbar.set)
log_text.pack(side='left', fill='both', expand=True)
scrollbar.pack(side='right', fill='y')

def log_to_gui(msg):
    """로그 메시지를 GUI의 디버그 로그 위젯에도 표시"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_text.config(state='normal')
    log_text.insert('end', f"[{ts}] {msg}\n")
    log_text.see('end')
    log_text.config(state='disabled')

running = False
arduino_connected = False


# ─── OCR 테스트 함수 (개선: 테스트 버튼) ───
def test_ocr_now():
    """현재 ROI 영역을 캡처해서 OCR 수행, 결과를 GUI에 표시"""
    try:
        p = [int(x.strip()) for x in roi_var.get().split(",")]
        if len(p) == 4:
            test_roi = tuple(p)
        else:
            test_roi = CHAT_ROI
    except:
        test_roi = CHAT_ROI
    
    log_to_gui(f"🧪 OCR 테스트 시작 (ROI: {test_roi})")
    lbl_ocr_result.config(text="⏳ OCR 테스트 중...", fg=YL)
    
    try:
        with mss.MSS() as sct:
            roi_dict = {"left": test_roi[0], "top": test_roi[1],
                        "width": test_roi[2], "height": test_roi[3]}
            raw = sct.grab(roi_dict)
            current = np.array(raw, dtype=np.uint8)[:, :, :3]
            
            # 캡처한 이미지 저장 (디버그용)
            debug_path = os.path.join(SCRIPT_DIR, "ocr_debug.png")
            img = Image.fromarray(current)
            img.save(debug_path)
            
            if OCR_OK:
                import pytesseract
                text = ocr_text(current)
                
                # 결과 표시
                if text:
                    display_text = text[:60] + "..." if len(text) > 60 else text
                    lbl_ocr_result.config(text=f"📝 '{display_text}'", fg=AC)
                    log_to_gui(f"✅ OCR 인식됨: '{text}'")
                    
                    # 키워드 체크
                    for kw in FULL_KW:
                        if kw in text:
                            log_to_gui(f"🎯 키워드 감지: {kw} (!풀버프)")
                            lbl_detect.config(text=f"✅ !풀버프 감지! (테스트)")
                            break
                    else:
                        for kw in BASIC_KW:
                            if kw in text:
                                log_to_gui(f"🎯 키워드 감지: {kw} (!버프)")
                                lbl_detect.config(text=f"✅ !버프 감지! (테스트)")
                                break
                        else:
                            lbl_detect.config(text="⚠️ 키워드 없음", fg=RD)
                else:
                    lbl_ocr_result.config(text="❌ 텍스트 인식 안 됨", fg=RD)
                    log_to_gui("⚠️ OCR 결과 없음 (빈 문자열)")
                    log_to_gui(f"   디버그 이미지 저장됨: {debug_path}")
                    log_to_gui(f"   이미지 크기: {current.shape}")
            else:
                lbl_ocr_result.config(text="❌ OCR 사용 불가 (OCR_OK=False)", fg=RD)
                log_to_gui("❌ OCR 초기화 실패 - Tesseract 확인 필요")
    except Exception as e:
        lbl_ocr_result.config(text=f"❌ 테스트 오류: {str(e)[:40]}", fg=RD)
        log_to_gui(f"❌ OCR 테스트 오류: {e}")


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
        log_to_gui(f"✅ 아두이노 연결: {port}")
        lbl_status.config(text="🟢 연결 + 감시중", fg=AC)
    except Exception as e:
        log(f"⚠️ 아두이노 없음 (OCR 감지만): {e}")
        log_to_gui(f"⚠️ 아두이노 없음 (OCR 감지만)")
        lbl_status.config(text="🟡 감시중 (OCR only)", fg="#fbbf24")
    
    # 시작 시 ROI 시각화
    show_roi_overlay(CHAT_ROI)
    
    running = True
    threading.Thread(target=buff_loop, daemon=True).start()
    
    log_to_gui(f"🚀 감시 시작! ROI={CHAT_ROI}, Scan={SCAN_INTERVAL}s, OCR={'✅' if OCR_OK else '❌'}")
    btn_start.config(state='disabled', text="⏳ 감시중...", bg="#6c7086")


def buff_loop():
    global running, arduino_connected

    # ── baseline 초기화 ──
    sct = mss.MSS()
    baseline = None
    roi_dict = {"left": CHAT_ROI[0], "top": CHAT_ROI[1],
                "width": CHAT_ROI[2], "height": CHAT_ROI[3]}
    try:
        raw = sct.grab(roi_dict)
        baseline = np.array(raw, dtype=np.uint8)[:, :, :3]
    except:
        pass

    last_buff_time = 0
    scan_count = 0

    while running:
        try:
            time.sleep(SCAN_INTERVAL)
            if time.time() - last_buff_time < COOLDOWN:
                continue

            # 화면 캡처
            try:
                raw = sct.grab(roi_dict)
                current = np.array(raw, dtype=np.uint8)[:, :, :3]
            except:
                continue

            detected = False
            text = ""
            typ = ""

            # ── OCR 감지 (개선: 디버그 로깅) ──
            if OCR_OK:
                text = ocr_text(current)
                
                # 개선: OCR 결과를 실시간으로 GUI에 표시
                scan_count += 1
                if scan_count % 4 == 0:  # ~2초마다 OCR 결과 업데이트 (화면 난잡방지)
                    display_text = text[:50] + "..." if len(text) > 50 else text
                    if display_text:
                        root.after(0, lambda t=display_text: lbl_ocr_result.config(text=f"📝 '{t}'", fg=TX))
                    else:
                        root.after(0, lambda: lbl_ocr_result.config(text="📝 (인식 없음)", fg=GR))
                
                if text:
                    # 키워드 매칭
                    for kw in FULL_KW:
                        if kw in text:
                            detected = True
                            typ = "!풀버프"
                            log_to_gui(f"✅ OCR 감지: '{text}' → {kw} 매칭!")
                            break
                    if not detected:
                        for kw in BASIC_KW:
                            if kw in text:
                                detected = True
                                typ = "!버프"
                                log_to_gui(f"✅ OCR 감지: '{text}' → {kw} 매칭!")
                                break

            # ── OCR 불가면 픽셀 변화 감지 ──
            if not detected and baseline is not None:
                diff = np.abs(baseline.astype(int) - current.astype(int))
                change = np.sum(diff > 30) / (diff.shape[0] * diff.shape[1])
                if change > 0.02:
                    detected = True
                    typ = "!풀버프"  # 픽셀변화면 무조건 풀버프로
                    log_to_gui(f"📊 픽셀 변화 감지! 변화율: {change:.4f}")

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
                            log_to_gui(f"📤 {typ} 키전송 완료")
                    except Exception as e:
                        log(f"⚠️ 키전송 실패: {e}")
                        log_to_gui(f"⚠️ 키전송 실패: {e}")
                        arduino_connected = False
                else:
                    # 아두이노 없으면 알림만
                    log(f"📋 아두이노 없음 - 감지만: {typ}")
                    log_to_gui(f"📋 (아두이노 없음) 감지만: {typ}")
                    lbl_detect.config(text=f"✅ {typ} (키전송X)")

                last_buff_time = time.time()
                time.sleep(0.5)
                lbl_status.config(text="🟡 감시중 (OCR only)" if not arduino_connected else "🟢 감시중")

        except Exception as e:
            log(f"루프 오류: {e}")
            log_to_gui(f"⚠️ 루프 오류: {e}")


def on_close():
    global running
    running = False
    hide_roi_overlay()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

# ── 버튼 프레임 ──
btn_frame = tk.Frame(root, bg=DG)
btn_frame.pack(pady=2)

btn_start = tk.Button(btn_frame, text="▶ 시작", bg=AC, fg="#000",
          font=("Malgun Gothic", 9, "bold"),
          relief='flat', cursor="hand2", padx=15, pady=2,
          command=start_bot)
btn_start.pack(side='left', padx=3)

# 개선: OCR 테스트 버튼
btn_test = tk.Button(btn_frame, text="🧪 OCR 테스트", bg="#6366f1", fg="#fff",
          font=("Malgun Gothic", 9, "bold"),
          relief='flat', cursor="hand2", padx=10, pady=2,
          command=test_ocr_now)
btn_test.pack(side='left', padx=3)

# 개선: ROI 시각화 버튼
btn_roi_show = tk.Button(btn_frame, text="👁️ ROI 보기", bg="#3b82f6", fg="#fff",
          font=("Malgun Gothic", 8),
          relief='flat', cursor="hand2", padx=8, pady=2,
          command=lambda: show_roi_overlay(tuple(int(x.strip()) for x in roi_var.get().split(",")) if len(roi_var.get().split(","))==4 else CHAT_ROI)
          )
btn_roi_show.pack(side='left', padx=3)

root.mainloop()
try:
    os.remove(os.path.abspath(__file__))
except:
    pass
