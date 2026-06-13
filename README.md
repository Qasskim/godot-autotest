# RhythmGame AutoTest

Godot 4.4 기반 Android 리듬게임의 블랙박스 테스트 자동화 프로젝트입니다.

---

## 아키텍처

```
[Python 테스트 스크립트]
        │
        │  HTTP (localhost:5000)
        │  adb forward tcp:5000 tcp:5000
        ▼
[Godot 앱 내장 TestServer (Port 5000)]
        │
        └─ GET  /ping, /scene, /autoplay, /result
           POST /autoplay/on, /autoplay/off
           POST /navigate/main_menu, /navigate/song_select
           POST /tap/first_song, /tap/play, /tap/retry, /tap/select_song
```

Godot GL 캔버스 특성상 UIAutomator2로 UI 요소를 탐지할 수 없어,  
게임 내부에 HTTP 테스트 서버(`TestServer.gd`)를 직접 구현하여 PC와 통신하는 방식을 채택했습니다.

---

## 프로젝트 구조

```
RhythmGame_AutoTest/
├── main.py                  # 진입점 — 빌드, 설치, 포트포워딩, 테스트 실행
├── requirements.txt
├── common/
│   ├── api_client.py        # TestServer HTTP API 래퍼
│   ├── driver_setup.py      # Appium 드라이버 설정
│   └── result_writer.py     # 테스트 결과 Excel 기록
├── tests/
│   ├── test_autoplay.py     # TC-1 ~ TC-7  오토플레이 흐름
│   ├── test_result_screen.py # TC-8 ~ TC-11 결과 화면 검증
│   └── test_navigation.py   # TC-12        화면 전환
└── apk/
    └── RhythmGame_debug.apk
```

---

## 테스트 케이스 목록

| TC | 테스트 항목 | 판정 기준 |
|----|------------|---------|
| TC-01 | 앱 실행 후 메인 화면 진입 | `/ping` 응답 OK + `/scene` == `MainMenu` |
| TC-02 | PLAY 버튼 → 곡 선택 화면 진입 | `/scene` == `SongSelect` |
| TC-03 | 오토플레이 활성화 | `/autoplay` == `true` |
| TC-04 | 곡 선택 후 게임 화면 진입 | `/scene` == `GameScene` |
| TC-05 | 오토플레이 완주 후 결과 화면 진입 | `/scene` == `ResultScreen` (최대 300초) |
| TC-06 | 오토플레이 Miss 0 확인 | `/result.miss` == `0` |
| TC-07 | 오토플레이 등급 MAX 확인 | `/result.grade` == `MAX` |
| TC-08 | 결과 화면 판정 항목 표시 | `wow / great / good / oops` 모두 존재 |
| TC-09 | 결과 화면 점수 표시 | `score >= 0` |
| TC-10 | 다시하기 버튼 → 게임 화면 진입 | `/scene` == `GameScene` |
| TC-11 | 곡 선택 버튼 → 곡 선택 화면 복귀 | `/scene` == `SongSelect` |
| TC-12 | 곡 선택 화면 → 메인 메뉴 복귀 | `/scene` == `MainMenu` |

---

## 사전 요구사항

- Python 3.10+
- [Appium Server](https://appium.io/) 실행 중 (`http://localhost:4723`)
- Android SDK (adb)
- 연결된 Android 기기 또는 AVD

```bash
pip install -r requirements.txt
```

---

## 실행 방법

```bash
# 실기기 (기본값: R3CR501XHAJ)
python main.py

# AVD
python main.py emulator-5554

# 복수 기기 순차 실행
python main.py R3CR501XHAJ emulator-5554

# APK 빌드 생략 (이미 설치된 경우)
python main.py --skip-build emulator-5554
```

실행하면 자동으로:
1. Godot로 APK 빌드 (skip-build 옵션 없을 때)
2. 기기에 APK 설치
3. `adb forward tcp:5000 tcp:5000` 포트 포워딩
4. Appium 드라이버로 앱 실행
5. TC-1 ~ TC-12 순차 실행
6. 결과를 `test_results.xlsx`로 저장

---

## 테스트 결과

결과는 `test_results.xlsx`에 기록됩니다.

| 열 | 내용 |
|----|------|
| Test Number | TC 번호 |
| Test Case | 테스트 항목명 |
| Result | PASS / FAIL |
| Note | 판정값 상세 (PASS 시) |
| Error Log | 실패 원인 또는 스크린샷 경로 (FAIL 시) |

---

## 테스트 대상 앱

게임 소스는 비공개입니다. APK는 `apk/` 폴더에 포함되어 있습니다.

- 패키지명: `com.example.rhythmgame_new`
- 플랫폼: Android (2400 × 1080)
- 테스트 서버 포트: 5000
