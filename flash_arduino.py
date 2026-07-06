"""아두이노 펌웨어 업로드 — RC 스타일 (avrdude + cs_firmware.hex).
COM 포트 자동감지, 진행률 표시."""
import subprocess, os, sys, serial.tools.list_ports

HERE = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_DIR = os.path.join(HERE, "firmware")
AVRDUDE = os.path.join(FIRMWARE_DIR, "avrdude", "avrdude.exe")
CONF = os.path.join(FIRMWARE_DIR, "avrdude", "avrdude.conf")
HEX = os.path.join(FIRMWARE_DIR, "뚱힐러.hex")

def find_arduino():
    """아두이노 COM 포트 자동감지."""
    for p in serial.tools.list_ports.comports():
        d = (p.description + p.manufacturer).lower()
        if any(k in d for k in ['arduino', 'ch340', 'cp210', 'usb serial', 'usb-serial']):
            return p.device
    return None

def flash(callback=None):
    """아두이노에 펌웨어 업로드. callback(pct, msg)으로 진행상황."""
    if not os.path.exists(AVRDUDE):
        return False, "avrdude.exe 없음"
    if not os.path.exists(HEX):
        return False, "cs_firmware.hex 없음"
    
    com = find_arduino()
    if not com:
        return False, "아두이노 COM 포트 못찾음"
    
    cmd = [
        AVRDUDE, "-C", CONF,
        "-c", "arduino",
        "-p", "atmega328p",
        "-P", com,
        "-b", "115200",
        "-U", f"flash:w:{HEX}:i"
    ]
    
    if callback:
        callback(10, f"아두이노 발견: {com}")
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                text=True, creationflags=0x08000000)
        for line in proc.stdout:
            line = line.strip()
            if "Writing" in line or "Reading" in line:
                if callback: callback(50, line[:60])
            elif "verifying" in line.lower():
                if callback: callback(80, "검증 중...")
        proc.wait()
        if proc.returncode == 0:
            if callback: callback(100, "업로드 완료!")
            return True, "완료"
        else:
            return False, f"avrdude 오류 (코드 {proc.returncode})"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    print("아두이노 찾는 중...")
    com = find_arduino()
    if not com:
        print("❌ 아두이노 없음")
        sys.exit(1)
    print(f"✅ {com} 발견. 업로드 중...")
    ok, msg = flash(lambda p, m: print(f"  {p}% {m}"))
    print(f"{'✅' if ok else '❌'} {msg}")
