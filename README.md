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
| `test_no_server.py` | `--no-server` 회귀 테스트(2026-11-07) — 자동화가 게임을 띄워도 서버에 접속하지 않음을 확인. 게임을 직접 띄우므로 포트 5000에 다른 게임이 있으면 중단 |
| `test_unit_lanes.py` | **단위 테스트 모듈 2** (2026-11-07) — 키 모드 그룹표(DESIGN §3), 레인 좌표, 물리 키 배치·키보드/터치 입력 처리(DESIGN §4), 터치 구역 변환, 한 번 누름에 판정되는 노트 규칙(DESIGN §5), 라인판정 보정. 모듈 1과 같은 방식으로 헤드리스 실행 |
| `test_unit_balance.py` | **단위 테스트 모듈 1** (2026-11-07) — 판정 창·EX 점수·등급 커트라인·게이지·콤보·마크를 DESIGN.md §5 수치로 검증(§6 롱/드래그 처리는 아직 미검증, 게이지 20% 비중만 포함). 게임 창·기기·TestServer 없이 Godot 헤드리스로 실행 |

### 단위 테스트(헤드리스) 구조

```
godot_unit/run_unit.gd        # 실행기: --headless --script 로 unit_<모듈>.gd 를 불러 @@UNIT@@ 줄로 결과 출력
godot_unit/unit_balance.gd    # 모듈 1 본체 (기대값은 DESIGN.md 수치를 직접 적음)
godot_unit/unit_selfcheck.gd  # 자체 점검: 메모리의 수치를 잠깐 바꿔 테스트가 변경을 잡는지 확인(게임 파일은 안 건드림)
godot_unit/unit_lanes.gd      # 모듈 2 본체 / unit_selfcheck_lanes.gd 는 모듈 2의 자체 점검
tests/godot_runner.py         # Python 래퍼 (Godot 경로·게임 프로젝트·격리 APPDATA는 환경변수 GODOT_EXE / GAME_PROJECT / AUTOTEST_APPDATA 로 변경)
tests/test_unit_balance.py    # 항목 하나 = pytest 케이스 하나, 기존 엑셀 리포트에 같이 기록
```

- 실행: `cd tests` 후 `pytest test_unit_balance.py` (기기 연결 불필요, 약 5초).
- 서버 없이 도는 테스트는 `@pytest.mark.no_server` 표시를 달면 TestServer 연결 확인과 실패 스크린샷 시도를 건너뜁니다.
- 명세와 코드가 다른데 어느 쪽이 맞는지 정해지지 않은 항목은 `test_unit_balance.py`의 `KNOWN_ISSUES`에 사유와 함께 올려 두고 xfail로 표시합니다(통과해 버리면 오히려 실패로 알려 줍니다).
- **서버 접속 금지 (2026-11-07 사고 이후)**: 게임을 그냥 띄우면 오토로드 `SupabaseHTTP._ready()`가 `ensure_session()`으로 **개발 서버에 익명 계정을 만들고**, 오토플레이로 치면 기록도 올라간다. 그래서 자동화에서 게임을 띄울 때는 반드시 `godot_runner.start_game()`을 쓴다. 이 함수는 항상 엔진 인자 `--no-server`를 붙이고(끄는 옵션 없음) APPDATA도 격리한다. `--no-server`는 디버그 빌드에서만 동작하며 서버로 나가는 모든 요청을 막는다. 단위 테스트(헤드리스)는 프레임을 기다리지 않아 서버에 접속하지 않는다(실행 후 격리 폴더에 `supabase_session.json`이 없어야 정상). `tests/test_no_server.py`가 이 효과(세션 파일 미생성, 서버 호출 차단, 외부 TCP 연결 0개)를 확인한다.
- 게임 사용자 폴더(`%APPDATA%\RhythmGame_New`)와 서버 세션을 건드리지 않도록 게임 프로세스에만 `APPDATA`를 `tests/reports/_appdata`로 바꿔 줍니다.

자세한 시나리오 설계(법칙, 케이스별 상태)는 [`tests/TEST_SCENARIO.md`](tests/TEST_SCENARIO.md) 참고.

---

## 테스트 대상 앱

대상 게임이 아직 개발 중이므로 디버그 빌드를 제공하고 있습니다. APK는 `apk/` 폴더에 포함되어 있습니다.
- 현재 음원도 제작중에 있어 키음 노트는 없는 상태입니다. 만약 필요하시다면 BMS를 컨버팅해서 사용하는 방법이 있습니다. 이 부분은 따로 문의주시면 변경한 BMS를 제공하겠습니다.

- 패키지명: `com.example.rhythmgame_new`
- 플랫폼: Android (2400 × 1080)
- 테스트 서버 포트: 5000 (디버그 빌드에서만 활성화)
