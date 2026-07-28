#include <Keyboard.h>
#include <Mouse.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>

// 무한 클릭 상태 저장 변수
bool autoClick = false;
unsigned long lastClickTime = 0;
unsigned long nextInterval = 100;

// Caterina 부트로더 매직키
#define CATERINA_MAGIC_ADDR ((uint16_t*)0x0800)
#define CATERINA_MAGIC_KEY  0x7777

/*
 * 중요: wdt_enable()으로 '시스템 리셋 WDT'를 켜면 Leonardo 1200bps 자동리셋이 깨짐.
 * → 평소엔 인터럽트-only WDT (키 떼고 재부팅). CDC 1200 soft-reset는 그대로 동작.
 * 펌업용 '!' 도 유지 (백업).
 */
ISR(WDT_vect) {
  autoClick = false;
  Keyboard.releaseAll();
  Mouse.release(MOUSE_LEFT);
  // 멈춤 복구: 짧게 시스템 리셋 (부트로더 아님)
  *CATERINA_MAGIC_ADDR = 0;
  wdt_enable(WDTO_15MS);
  while (true) {}
}

void enableHangWdt() {
  cli();
  wdt_reset();
  MCUSR &= ~(1 << WDRF);
  // 변경 허용 시퀀스 후: WDIE만 (WDE=0) + ~4초
  WDTCSR |= (1 << WDCE) | (1 << WDE);
  WDTCSR = (1 << WDIE) | (1 << WDP3);  // WDP3=1 → 4.0s, 인터럽트만
  sei();
}

void enterBootloader() {
  autoClick = false;
  Keyboard.releaseAll();
  Mouse.release(MOUSE_LEFT);
  Serial.flush();
  Serial.end();
  delay(20);
  cli();
  *CATERINA_MAGIC_ADDR = CATERINA_MAGIC_KEY;
  wdt_enable(WDTO_15MS);
  while (true) {}
}

void humanPress(uint8_t k) {
  Keyboard.press(k);
  delay(random(80, 150));
  Keyboard.release(k);
  wdt_reset();
}

void setup() {
  cli();
  MCUSR &= ~(1 << WDRF);
  wdt_disable();
  sei();

  Serial.begin(9600);
  Serial.setTimeout(10);
  Keyboard.begin();
  Mouse.begin();
  Keyboard.releaseAll();
  Mouse.release(MOUSE_LEFT);

  randomSeed(analogRead(A0));

  delay(3000);
  enableHangWdt();  // 인터럽트 WDT — 1200bps 자동펌업 유지
}

void loop() {
  wdt_reset();

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

  while (Serial.available() > 0) {
    wdt_reset();
    char cmd = Serial.read();

    if (cmd == '!') {
      enterBootloader();
    }

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

    // DDONG-WDT3 = 워치독(인터럽트) + 1200 자동펌업 유지 + '!'
    if (cmd == 'V') {
      Serial.println(F("DDONG-WDT3"));
      continue;
    }

    switch (cmd) {
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

      case '1': humanPress(KEY_F1); break;
      case '2': humanPress(KEY_F2); break;
      case '3': humanPress(KEY_F3); break;
      case '4': humanPress(KEY_F4); break;
      case '5': humanPress(KEY_F5); break;
      case '6': humanPress(KEY_F6); break;
      case '7': humanPress(KEY_F7); break;
      case '8': humanPress(KEY_F8); break;
      case '9': humanPress(KEY_F9); break;
      case 'X': humanPress(KEY_F10); break;
      case 'Y': humanPress(KEY_F11); break;
      case 'Z': humanPress(KEY_F12); break;
    }
  }
}
