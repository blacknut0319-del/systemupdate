#include <Keyboard.h>
#include <Mouse.h>
#include <avr/wdt.h>

// 무한 클릭 상태 저장 변수
bool autoClick = false;
unsigned long lastClickTime = 0;
unsigned long nextInterval = 100;

// Caterina 부트로더 매직키 (펌업 '!' 명령용)
#define CATERINA_MAGIC_ADDR ((uint16_t*)0x0800)
#define CATERINA_MAGIC_KEY  0x7777

void releaseAllMouse() {
  Mouse.release(MOUSE_LEFT);
  Mouse.release(MOUSE_RIGHT);
  Mouse.release(MOUSE_MIDDLE);
}

void humanClick(uint8_t button) {
  Mouse.press(button);
  delay(random(20, 50));
  Mouse.release(button);
}

void enterBootloader() {
  autoClick = false;
  Keyboard.releaseAll();
  releaseAllMouse();
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
}

void setup() {
  wdt_disable();

  Serial.begin(9600);
  Serial.setTimeout(10);
  Keyboard.begin();
  Mouse.begin();
  Keyboard.releaseAll();
  releaseAllMouse();

  randomSeed(analogRead(A0));
}

void loop() {
  if (autoClick) {
    unsigned long currentTime = millis();
    if (currentTime - lastClickTime >= nextInterval) {
      Mouse.press(MOUSE_LEFT);
      delay(random(30, 75));
      Mouse.release(MOUSE_LEFT);

      lastClickTime = currentTime;
      nextInterval = random(85, 180);
    }
  }

  while (Serial.available() > 0) {
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

    // 마우스: K=좌클릭 J=우클릭 M=휠클릭 O=휠위 L=휠아래
    if (cmd == 'K') { humanClick(MOUSE_LEFT); continue; }
    if (cmd == 'J') { humanClick(MOUSE_RIGHT); continue; }
    if (cmd == 'M') { humanClick(MOUSE_MIDDLE); continue; }
    if (cmd == 'O') { Mouse.move(0, 0, 1); continue; }
    if (cmd == 'L') { Mouse.move(0, 0, -1); continue; }

    if (cmd == 'U') {
      autoClick = false;
      Keyboard.releaseAll();
      releaseAllMouse();
      delay(5);
      continue;
    }

    // Shift: H=누름 R=뗌 | Alt: (=누름 )=뗌 | Ctrl: [=누름 ]=뗌
    if (cmd == 'H') { Keyboard.press(KEY_LEFT_SHIFT); autoClick = false; continue; }
    if (cmd == 'R') { Keyboard.release(KEY_LEFT_SHIFT); autoClick = false; continue; }
    if (cmd == '(') { Keyboard.press(KEY_LEFT_ALT); continue; }
    if (cmd == ')') { Keyboard.release(KEY_LEFT_ALT); continue; }
    if (cmd == '[') { Keyboard.press(KEY_LEFT_CTRL); continue; }
    if (cmd == ']') { Keyboard.release(KEY_LEFT_CTRL); continue; }
    if (cmd == 'T') { autoClick = !autoClick; continue; }

    if (cmd == 'V') {
      Serial.println(F("DDONG-V4"));
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
            delay(50);
          }
        }
        Keyboard.releaseAll();
        break;

      // D=Delete F=End P=PageDown
      case 'D': humanPress(KEY_DELETE); break;
      case 'F': humanPress(KEY_END); break;
      case 'P': humanPress(KEY_PAGE_DOWN); break;

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
