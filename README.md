# RhythmGame AutoTest

Godot 4.4 기반 Android 리듬게임의 테스트 자동화 프로젝트입니다.

> 이전 버전은 Appium/UIAutomator2 기반이었으나, Godot의 OpenGL 캔버스 특성상
> UIAutomator2가 개별 UI 요소를 인식하지 못해(화면 전체가 View 1개로만 잡힘)
> 이미지 매칭 방식도 시도했지만 신뢰성 문제로 폐기했습니다.
> 현재는 게임 내부에 디버그 전용 HTTP 서버를 직접 심어 제어/검증하는 방식으로 전환했습니다.

---

## 아키텍처

```
[Python pytest 테스트 스크립트]
        │
        │  HTTP (localhost:5000)
        │  adb forward tcp:5000 tcp:5000
        ▼
[Godot 앱 내장 TestServer (디버그 빌드 전용, 포트 5000)]
        │
        ├─ 씬 전환:      GET /scene, POST /navigate/main_menu, /navigate/song_select
        ├─ 화면별 버튼:  POST /tap/mainmenu_play, /tap/settings_back,
        │                /tap/songselect_tab_world, /tap/song_at?index=N, ...
        ├─ 게임플레이:   POST /autoplay/on|off, /tap/pause_toggle,
        │                /tap/pause_speed_up|down, /pause/calibration, /touchzone/on|off
        └─ 결과 조회:    GET /result, /best, /game_state, /songs, /screenshot
```

이 방식은 엄밀히는 **블랙박스가 아니라 그레이박스**에 가깝습니다. 실제 유저가 쓸 수 없는
디버그 전용 신호(인덱스 지정 곡 선택, 내부 결과 JSON 조회 등)로 게임을 직접 제어/검증하기
때문입니다. 대신 Godot GL 캔버스에서 UI 자동화가 원천적으로 막히는 문제를 우회하면서도,
실제로 동작하는 게임 로직(판정/점수/게이지/타이밍)은 처음부터 끝까지 실제 앱에서 검증합니다.

---

## 프로젝트 구조

```
RhythmGame_AutoTest/
├── 1_install_and_launch.bat   # APK 설치 + 포트포워딩 + 앱 실행
├── 2_run_tests.bat            # 기본 테스트 스위트 실행 (앱을 안 끔)
├── 3_run_full_scenario.bat    # 전체 시나리오 테스트 (마지막에 앱 종료)
├── apk/
│   └── RhythmGame_debug.apk
└── tests/
    ├── client.py               # TestServer HTTP 클라이언트 래퍼
    ├── conftest.py              # pytest 공용 fixture + 엑셀 결과 기록 훅
    ├── result_writer.py         # 결과 엑셀(xlsx) 기록 (PASS/FAIL/N/A + 실패 스크린샷 삽입)
    ├── requirements.txt
    ├── TEST_SCENARIO.md         # 전체 시나리오 테스트의 설계 문서
    ├── test_flow.py             # 씬 전환 플로우
    ├── test_autoplay.py         # 오토플레이 결과 검증
    ├── test_marks.py            # 마크 시스템 검증
    ├── test_best_record.py      # 개인 최고기록 갱신/비교
    └── test_full_scenario.py    # 모든 화면/버튼 + 곡 전체 순회 + 정상종료
```

---

## 사전 요구사항

- Python 3.10+
- Android SDK Platform-Tools (`adb`)
- USB 디버깅이 켜진 Android 실기기 (연결 상태에서 `adb devices`로 확인)

Python 패키지는 배치 파일 실행 시 자동으로 설치됩니다 (`pip install -r tests/requirements.txt`).

---

## 실행 방법

1. **`1_install_and_launch.bat`** 실행 — 기기에 APK 설치, 포트포워딩, 앱 실행까지 한 번에 처리
2. **`2_run_tests.bat`** 실행 — 기본 테스트 스위트(씬 전환/오토플레이/마크/최고기록) 실행. 반복 실행 가능
3. **`3_run_full_scenario.bat`** 실행 — 모든 화면/버튼 진입 + 곡 목록 전체 순회 + 정상종료까지 한 번에 검증.
   **마지막 단계에서 앱을 실제로 종료시키므로**, 다시 테스트하려면 1번부터 재실행

각 배치 파일은 단독으로 실행 가능하며, 실행 중 진행 상황이 CMD 창에 그대로 표시됩니다.

---

## 테스트 결과

`tests/reports/test_results.xlsx`에 기록됩니다. 실행할 때마다 파일은 누적되고,
`일-월-년도` 이름의 새 시트가 추가됩니다 (같은 날 재실행 시 `(2)`, `(3)`... 붙음).

| 열 | 내용 |
|----|------|
| Test Number | 세부 항목 번호 |
| Test Case | 테스트 항목명 |
| Result | PASS / FAIL / SKIP / N/A |
| Note | 판정값 상세 또는 실패 사유 |
| Screenshot | 실패 시 캡처된 스크린샷 이미지가 셀에 직접 삽입됨 |

`N/A` 항목은 재현이 어렵거나(예외 팝업) 미구현 기능(곡 폴더 선택)으로, 비고란에 사유가 기록됩니다.

---

## 테스트 항목 개요

| 파일 | 내용 |
|------|------|
| `test_flow.py` | 씬 전환 플로우 (ping, navigate, 전체 플로우) |
| `test_autoplay.py` | 오토플레이 결과 검증 (점수, 정확도, 판정합계) |
| `test_marks.py` | 마크 시스템 검증 (perfect/allcombo/allgood/clear/failed) |
| `test_best_record.py` | 개인 최고기록 갱신/비교 |
| `test_full_scenario.py` | `TEST_SCENARIO.md` 기반 — 모든 화면/버튼 진입, 곡 목록 전체 순회, 정상종료. 단독 실행 전용 |

자세한 시나리오 설계(법칙, 케이스별 상태)는 [`tests/TEST_SCENARIO.md`](tests/TEST_SCENARIO.md) 참고.

---

## 테스트 대상 앱

게임 소스는 비공개입니다. 디버그 빌드 APK는 `apk/` 폴더에 포함되어 있습니다.

- 패키지명: `com.example.rhythmgame_new`
- 플랫폼: Android (2400 × 1080)
- 테스트 서버 포트: 5000 (디버그 빌드에서만 활성화)
