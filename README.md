# systemupdate — 뚱 시리즈 자동업데이트

한 저장소에 **앱마다 폴더를 분리**합니다. 헷갈리면 아래만 보면 됩니다.

| 앱 | 폴더 | 버전 파일 | Release 파일 | 태그 예 |
|----|------|-----------|--------------|---------|
| **뚱헌터** | [`뚱헌터/`](뚱헌터/) | `뚱헌터/version.json` | `ddonghunter.exe` | `v1.4.xxx` |
| **뚱법사** | [`뚱법사/`](뚱법사/) | `뚱법사/version.json` | `ddungmage.exe` / `뚱법사.exe` | `v0.1.xxx` |
| **뚱힐러** | [`뚱힐러/`](뚱힐러/) | (레거시: 루트 zip / firmware) | 기존 `hp_start` 등 | — |

## 규칙 (중요)

1. **각 앱은 자기 폴더의 `version.json`만 수정**합니다. 다른 앱 폴더는 건드리지 않습니다.
2. **exe는 Release에만** 올립니다 (git 100MB 제한). `version.json`의 `url`이 그 Release를 가리킵니다.
3. **펌웨어(아두이노 HEX)** 는 공통: [`firmware/`](firmware/)  
   - 뚱힐러 HEX: `firmware/뚱힐러.hex` (뚱법사 펌업도 동일 HEX 사용)
4. 루트에 남아 있는 `ddonghunter_version.json`, `hp_start.zip` 등은 **구버전 호환용**입니다. 새 배포는 위 표의 폴더를 사용하세요.

## 폴더 한눈에

```
systemupdate/
├── README.md          ← 지금 이 파일
├── 뚱헌터/
│   └── version.json   ← 헌터 자동업데이트
├── 뚱법사/
│   └── version.json   ← 법사 자동업데이트
├── 뚱힐러/
│   └── README.md      ← 힐러 안내 (레거시 경로)
└── firmware/
    └── 뚱힐러.hex
```

## 옆 PC / 공유폴더

로컬 공유는 `\\DESKTOP-60DJASL\ReceivedFiles\공유_최신\` 아래에도 앱별 폴더로 둡니다.

- `공유_최신\ddonghunter.exe` — 뚱헌터
- `공유_최신\뚱법사\` — 뚱법사 (`뚱법사_설치실행.bat`)
