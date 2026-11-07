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
| `test_unit_timing.py` | **단위 테스트 모듈 3** (2026-11-08) — 박자(`TimeSignature`)와 타이밍 테이블(`ChartTiming`: 마디 길이 공식, BPM·박자 변경 이벤트, 조회 경계). 기대값은 공식에서 손으로 계산한 ms |
| `test_data_charts.py` | **데이터 검증 모듈 6** (2026-11-08) — 수록 17곡 68채보와 튜토리얼 채보의 구조·메타·키음 파일·노트 필드·드래그 체인·타이밍·레인믹스 구간, 곡 폴더 구성(manifest, full_mix, preview, 자켓). 파일만 읽음(DESIGN §8·§9·§14) |
| `test_data_locale.py` | **데이터 검증 모듈 7** (2026-11-08) — 번역 CSV(키 중복·빈 값·자리표시자)와 코드가 쓰는 키의 존재. 영어 타이틀 키 노출 사고(11-05) 재발 방지 |
| `test_unit_locale.py` | **모듈 7(Godot 쪽)** — 임포트된 번역이 CSV와 같은지, `Locale`의 `has`/`t_or`/`tf` 동작 |
| `test_unit_signing.py` | **모듈 8** (2026-11-08) — 공식 채보 서명. 게임의 검증 함수(`ChartLoader._verify_signature`, RSA-SHA256)로 수록 17곡 `manifest.json`·68채보의 `.sig`가 현재 파일과 맞는지, 변조·빈 서명·다른 파일 서명을 거부하는지 확인 |
| `test_unit_drag.py` | **모듈 10** (2026-11-08) — 드래그 노트 처리(DESIGN §6). `DragNoteVisual`의 궤적 보간(웨이포인트 사이 X·레인), 정상 홀드, 궤적 이탈, 끝 앞 Oops 창(경계 포함), 헤드 미스와 구제, 재진입, 허용 폭 경계, 오토플레이·키보드 |
| `test_unit_scroll.py` | **모듈 11** (2026-11-08) — 스크롤 계산(`NotePositionCalculator`: 누적 스크롤 테이블·BPM 변속·배속·노트 Y·원근 배율), 화면 비례 레이아웃(`ScreenLayout._rebuild`: 11가지 해상도에서 레인이 화면 폭을 채우고 판정선·스폰이 비례, 비정상 크기 무시), 도트 폰트 크기 규칙(설계 크기의 정수 배수, DESIGN §13-2) |
| `test_unit_audio.py` | **모듈 12(게임 쪽)** (2026-11-08) — 키음 음량(velocity/64×volume/100)·pan(밸런스 방식, 반대쪽 채널만 cos 감쇠) 공식과 값 자르기를 합성 스테레오 WAV로 검증하고 수치표를 내보냄 |
| `test_cross_formula.py` | **교차 비교** — 시퀀서(C#, `csharp_check/SeqFormulaCheck`가 시퀀서 소스 `NoteData.cs`·`PanLaw.cs`를 그대로 연결해 `dotnet publish`한 콘솔)와 게임의 음량·pan 결과가 255개 pan·40개 음량 조합에서 같은지, 문서 공식과 맞는지, 자르기와 기준값 미기록이 같은지 |
| `test_unit_hold.py` | **모듈 9** (2026-11-08) — 롱노트 처리(DESIGN §6). `LongNoteVisual`을 곡 시계와 터치 입력을 직접 움직여 검증: 정상 홀드·틱 게이지, 끝 앞 창 밖 이탈(Miss·콤보 0), 끝 앞 Oops 창(250ms, 경계 포함) 안에서 뗌, 헤드 미스와 구제, 이탈 뒤 재진입, 오토플레이·키보드 |
| `test_unit_offline.py` | **단위 테스트 모듈 5** (2026-11-08) — 서버 접속 차단 가드. 프레임을 실제로 돌려 오토로드 `_ready`가 실행돼도 `--no-server`로 세션이 만들어지지 않고 서버 조회·쓰기가 차단되는지 확인 |
| `test_unit_lanemix.py` | **단위 테스트 모듈 4** (2026-11-08) — 레인믹스 상태(`LaneMixState`: 섹션·키모드 랜덤/슈퍼랜덤·구간 경계·활성화), 진입 안내(`LaneMixEntry`: 2마디 전 안내·수락·3초 미리보기), 노트 랜덤(`NoteRandomizer`: RANDOM/S-RANDOM, 드래그 체인 회피) |
| `test_unit_lanes.py` | **단위 테스트 모듈 2** (2026-11-07) — 키 모드 그룹표(DESIGN §3), 레인 좌표, 물리 키 배치·키보드/터치 입력 처리(DESIGN §4), 터치 구역 변환, 한 번 누름에 판정되는 노트 규칙(DESIGN §5), 라인판정 보정. 모듈 1과 같은 방식으로 헤드리스 실행 |
| `test_unit_balance.py` | **단위 테스트 모듈 1** (2026-11-07) — 판정 창·EX 점수·등급 커트라인·게이지·콤보·마크를 DESIGN.md §5 수치로 검증(§6 롱/드래그 처리는 아직 미검증, 게이지 20% 비중만 포함). 게임 창·기기·TestServer 없이 Godot 헤드리스로 실행 |

### 단위 테스트(헤드리스) 구조

```
godot_unit/run_unit.gd        # 실행기: --headless --script 로 unit_<모듈>.gd 를 불러 @@UNIT@@ 줄로 결과 출력
godot_unit/unit_balance.gd    # 모듈 1 본체 (기대값은 DESIGN.md 수치를 직접 적음)
godot_unit/unit_selfcheck.gd  # 자체 점검: 메모리의 수치를 잠깐 바꿔 테스트가 변경을 잡는지 확인(게임 파일은 안 건드림)
godot_unit/unit_lanes.gd      # 모듈 2 본체 / unit_selfcheck_lanes.gd 는 모듈 2의 자체 점검
godot_unit/unit_timing.gd     # 모듈 3 본체 / unit_lanemix.gd 는 모듈 4 본체 (모듈 3·4는 바꿀 수 있는 전역 수치가 없어 자체 점검 없음 — 기대값을 손계산으로 적음)
tests/godot_runner.py         # Python 래퍼 (Godot 경로·게임 프로젝트·격리 APPDATA는 환경변수 GODOT_EXE / GAME_PROJECT / AUTOTEST_APPDATA 로 변경)
tests/test_unit_balance.py    # 항목 하나 = pytest 케이스 하나, 기존 엑셀 리포트에 같이 기록
```

- 실행: `cd tests` 후 `pytest test_unit_balance.py test_unit_lanes.py test_unit_timing.py test_unit_lanemix.py` (기기 연결 불필요, 모듈마다 5~20초). 모듈이 스크립트 오류로 멈추면 실행기의 감시 타이머가 90초 뒤 오류 원문과 함께 끝낸다.
- 서버 없이 도는 테스트는 `@pytest.mark.no_server` 표시를 달면 TestServer 연결 확인과 실패 스크린샷 시도를 건너뜁니다.
- 명세와 코드가 다른데 어느 쪽이 맞는지 정해지지 않은 항목은 `test_unit_balance.py`의 `KNOWN_ISSUES`에 사유와 함께 올려 두고 xfail로 표시합니다(통과해 버리면 오히려 실패로 알려 줍니다).
- **모듈이 스크립트 오류로 중간에 끝나면 검사가 조용히 빠진다** (2026-11-08 모듈 2에서 발견: 터치 구역·터치 입력 검사 40건이 뷰포트 null 오류로 만들어지지 않았는데 "통과"로 보고됨). 그래서 `run_unit_module`은 엔진의 `SCRIPT ERROR`를 모아 모듈마다 `스크립트 오류 없음` TC를 추가하고, 예상된 오류만 `allow_errors`로 허용한다. 뷰포트·오토로드 `_ready`가 필요한 모듈은 `var needs_frames := true`를 두면 실행기가 프레임 2번을 기다린 뒤 시작한다(`--no-server`가 항상 붙어 서버에는 접속하지 않음).
- **서버 접속 금지 (2026-11-07 사고 이후)**: 게임을 그냥 띄우면 오토로드 `SupabaseHTTP._ready()`가 `ensure_session()`으로 **개발 서버에 익명 계정을 만들고**, 오토플레이로 치면 기록도 올라간다. 그래서 자동화에서 게임을 띄울 때는 반드시 `godot_runner.start_game()`을 쓴다. 이 함수는 항상 엔진 인자 `--no-server`를 붙이고(끄는 옵션 없음) APPDATA도 격리한다. `--no-server`는 디버그 빌드에서만 동작하며 서버로 나가는 모든 요청을 막는다. 단위 테스트(헤드리스)는 프레임을 기다리지 않아 서버에 접속하지 않는다(실행 후 격리 폴더에 `supabase_session.json`이 없어야 정상). `tests/test_no_server.py`가 이 효과(세션 파일 미생성, 서버 호출 차단, 외부 TCP 연결 0개)를 확인한다.
- **헤드리스 실행기도 항상 `--no-server`를 붙인다** (2026-11-08 사고: 모듈이 스크립트 오류로 멈춰 감시 타이머 전까지 프레임이 돌았고, 그동안 오토로드 `_ready`가 개발 서버에 익명 계정을 만들었다). 모듈 5가 이 가드를 확인한다.
- 게임 사용자 폴더(`%APPDATA%\RhythmGame_New`)와 서버 세션을 건드리지 않도록 게임 프로세스에만 `APPDATA`를 `tests/reports/_appdata`로 바꿔 줍니다.

자세한 시나리오 설계(법칙, 케이스별 상태)는 [`tests/TEST_SCENARIO.md`](tests/TEST_SCENARIO.md) 참고.

---

## 테스트 대상 앱

대상 게임이 아직 개발 중이므로 디버그 빌드를 제공하고 있습니다. APK는 `apk/` 폴더에 포함되어 있습니다.
- 현재 음원도 제작중에 있어 키음 노트는 없는 상태입니다. 만약 필요하시다면 BMS를 컨버팅해서 사용하는 방법이 있습니다. 이 부분은 따로 문의주시면 변경한 BMS를 제공하겠습니다.

- 패키지명: `com.example.rhythmgame_new`
- 플랫폼: Android (2400 × 1080)
- 테스트 서버 포트: 5000 (디버그 빌드에서만 활성화)
