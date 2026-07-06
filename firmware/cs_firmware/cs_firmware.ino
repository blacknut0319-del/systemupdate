#include <Keyboard.h>
#include <Mouse.h>

bool autoClick = false; 
unsigned long lastClickTime = 0;
unsigned long nextInterval = 100;

void humanPress(uint8_t k) {
  Keyboard.press(k);
  delay(random(80, 150)); 
  Keyboard.release(k);
}

void setup() {
  Serial.begin(9600); 
  Serial.setTimeout(10); 
  Keyboard.begin();
  Mouse.begin();
  randomSeed(analogRead(A0));
  delay(3000);
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
      case 'A': humanPress(KEY_F9); break;
      case 'B': humanPress(KEY_F9); delay(random(70, 130)); humanPress(KEY_F9); break;
      case 'E': humanPress(KEY_F5); break;
      case 'C': 
        autoClick = false;
        Keyboard.releaseAll(); 
        delay(10);
        Keyboard.press(KEY_F8);
        delay(random(1100, 1400)); 
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
