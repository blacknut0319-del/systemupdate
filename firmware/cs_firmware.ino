#include <Keyboard.h>
#include <Mouse.h>
#include <avr/wdt.h>

// 무한 클릭 상태 저장 변수
bool autoClick = false; 
unsigned long lastClickTime = 0;
unsigned long nextInterval = 100;

// 🛡️ [보안] 키보드 입력 시 사람이 누르는 것처럼 랜덤 시간 적용 (백업 원본 유지)
void humanPress(uint8_t k) {
  Keyboard.press(k);
  delay(random(80, 150)); 
  Keyboard.release(k);
  wdt_reset();  // 연속 키입력 중에도 워치독 만료 방지
}

void setup() {
  wdt_disable();  // 워치독 리셋 직후 상태가 남아있으면 부팅루프에 빠질 수 있어 가장 먼저 꺼둠
  Serial.begin(9600); 
  Serial.setTimeout(10); 
  Keyboard.begin();
  Mouse.begin();
  Keyboard.releaseAll();       // 🔧 리셋 직전에 키가 눌린 채로 멈췄어도 부팅 시 무조건 초기화
  Mouse.release(MOUSE_LEFT);
  
  // 완벽한 난수 생성을 위해 연결되지 않은 A0 핀의 노이즈 값을 시드로 사용
  randomSeed(analogRead(A0));
  
  delay(3000); // 업로드 후 준비 시간
  wdt_enable(WDTO_4S);  // 🔧 loop()가 4초 안에 안 돌면(=멈추면) 자동 재부팅 — 힐키 눌린 채 멈추는 버그 자동복구
}

void loop() {
  wdt_reset();  // 🔧 정상적으로 돌고 있다는 신호(pet). 4초 넘게 안 오면 워치독이 강제 리셋
  // 🛡️ [보안] 무한 클릭 로직의 인간화 (백업 원본 유지)
  if (autoClick) {
    unsigned long currentTime = millis();
    if (currentTime - lastClickTime >= nextInterval) {
      Mouse.press(MOUSE_LEFT);
      delay(random(30, 75)); 
      Mouse.release(MOUSE_LEFT);
      wdt_reset();
      
      lastClickTime = currentTime;
      nextInterval = random(85, 180); 
    }
  }

  // 시리얼 명령 수신부
  while (Serial.available() > 0) {
    wdt_reset();
    char cmd = Serial.read();

    if (cmd == '<') {
      int dx = Serial.parseInt();
      int dy = Serial.parseInt();
      if (Serial.read() == '>') {
        Mouse.move(dx, dy, 0);
      }
      continue;
    }

    if (cmd == 'K') {
      Mouse.press(MOUSE_LEFT);
      delay(random(20, 50));
      Mouse.release(MOUSE_LEFT);
      continue;
    }

    if (cmd == 'U') { 
      autoClick = false;
      Keyboard.releaseAll(); 
      delay(5); 
      continue;
    } 

    if (cmd == 'H') { Keyboard.press(KEY_LEFT_SHIFT); autoClick = true; continue; } 
    if (cmd == 'R') { Keyboard.release(KEY_LEFT_SHIFT); autoClick = false; continue; } 
    if (cmd == 'T') { autoClick = !autoClick; continue; } 

    switch(cmd) {
      case 'A': 
        humanPress(KEY_F9); 
        break;
        
      case 'B': 
        humanPress(KEY_F9);
        delay(random(70, 130));
        humanPress(KEY_F9);
        break;
        
      case 'E': 
        humanPress(KEY_F5); 
        break;
        
      case 'C': 
        autoClick = false;
        Keyboard.releaseAll(); 
        delay(10);
        Keyboard.press(KEY_F8);
        // 귀환 길게누름(~1.1~1.4초) 중에도 워치독 만료되지 않게 중간 reset
        {
          unsigned long hold = random(1100, 1400);
          unsigned long t0 = millis();
          while (millis() - t0 < hold) {
            wdt_reset();
            delay(50);
          }
        }
        Keyboard.releaseAll();
        break;
        
      
      // ==========================================
      // 💡 [신규] 줍기(F4) & 타이머 & 독 해독
      // ==========================================
      case '1': humanPress(KEY_F1); break;   
      case '2': humanPress(KEY_F2); break;   
      case '3': humanPress(KEY_F3); break;   // F3 단축키창 이동 (UDP 매크로)
      case '4': humanPress(KEY_F4); break;   // 💡 F4 (자동 줍기) 추가!
      case '5': humanPress(KEY_F5); break;   
      case '6': humanPress(KEY_F6); break;   
      case '7': humanPress(KEY_F7); break;   // F7 (UDP 매크로)
      case '8': humanPress(KEY_F8); break;
      case '9': humanPress(KEY_F9); break;
      case 'X': humanPress(KEY_F10); break;
      case 'Y': humanPress(KEY_F11); break;
      case 'Z': humanPress(KEY_F12); break;

    }
  }
}
