# RhythmGame AutoTest

Godot 4.7 기반 Android 리듬게임 **ASTRAL RAIN**(2026-11-05 itch.io 프로토타입 공개)의 테스트 자동화 프로젝트입니다.

> 이전 버전은 Appium/UIAutomator2 기반이었으나, Godot의 OpenGL 캔버스 특성상
> UIAutomator2가 개별 UI 요소를 인식하지 못해(화면 전체가 View 1개로만 잡힘)
> 이미지 매칭 방식도 시도했지만 신뢰성 문제로 폐기했습니다.
> 현재는 게임 내부에 디버그 전용 HTTP 서버를 직접 심어 제어/검증하는 방식으로 전환했습니다.

---

## 아키텍처

```
[Python pytest 테스트 스크립트]
        │
        │  HTTP (127.0.0.1:5000)
        │  PC  : 자동화가 Godot 로 게임을 직접 띄운다 (폰 불필요, 지금의 기본 경로)
        │  폰  : adb forward tcp:5000 tcp:5000
        ▼
[Godot 앱 내장 TestServer — 디버그 빌드 전용, 포트 5000, 요청 경로 111종 (GET 30 / POST 81)]
        │
        ├─ 화면 읽기:  GET /scene, /screen_texts, /songs, /result, /best, /game_state, /screenshot
        ├─ 조작:       POST /screen_press?text=, /screen_input, /screen_option, /screen_tab,
        │              /screen_slider, /screen_press_nth, /debug_click, /debug_drag, /back,
        │              /navigate/*, /tap/*
        ├─ 플레이:     POST /autoplay/on|off, /debug_autoplay_live, /debug_goto_gameplay,
        │              /debug_press_plan, /debug_replay_last, /tap/pause_toggle, /touchzone/on|off
        ├─ 상태:       GET /debug_notes, /debug_judgment_log, /debug_lanemix_prompt
        └─ 서버:       POST /supabase_debug_login, /debug_service, GET /supabase_session, /remote_config
```

이 방식은 엄밀히는 **블랙박스가 아니라 그레이박스**에 가깝습니다. 실제 유저가 쓸 수 없는
디버그 전용 신호(인덱스 지정 곡 선택, 내부 결과 JSON 조회 등)로 게임을 직접 제어/검증하기
때문입니다. 대신 Godot GL 캔버스에서 UI 자동화가 원천적으로 막히는 문제를 우회하면서도,
실제로 동작하는 게임 로직(판정/점수/게이지/타이밍)은 처음부터 끝까지 실제 앱에서 검증합니다.

---

## 프로젝트 구조

```
RhythmGame_AutoTest/
├── COVERAGE.md                 # 시험 범위 대조표 (게임 스크립트 80개·데이터·서버 함수 ↔ 시험)
├── 1_install_and_launch.bat    # 폰 실기용 (아래 "폰 실기로 돌릴 때" 참고)
├── 2_run_tests.bat             # 〃
├── 3_run_full_scenario.bat     # 〃
├── csharp_check/               # 시퀀서(C#)의 음량·pan 공식을 그대로 돌려 게임과 비교하는 콘솔
├── godot_unit/                 # Godot 헤드리스 단위 테스트 본체 unit_*.gd 31개 + 실행기 run_unit.gd
└── tests/
    ├── run_all.py              # 풀 테스트 진입점 (unit → integration → server → full)
    ├── tc_export.py            # 실행 결과 → 사람이 읽는 TC 형식 엑셀
    ├── tc_catalog/             # TC 문장(대분류·중분류·사전 조건·절차·기대 결과) JSON
    ├── client.py               # TestServer HTTP 클라이언트 래퍼
    ├── godot_runner.py         # 게임·헤드리스 실행 래퍼 (항상 --no-server, APPDATA 격리)
    ├── conftest.py             # pytest 공용 fixture + 엑셀 결과 기록 훅
    ├── result_writer.py        # 결과 엑셀(xlsx) 기록 (PASS/FAIL/N/A + 실패 스크린샷 삽입)
    ├── screen_helpers.py       # 화면에 보이는 글자로 확인하는 공용 도구
    ├── server_helpers.py       # 서버 테스트 보조
    ├── server_ledger.py        # 서버에 만든 테스트 계정 장부
    ├── cleanup_server.py       # 장부에 적힌 테스트 데이터 정리 (기본은 목록만)
    ├── coverage_audit.py       # COVERAGE.md 점검 도구
    ├── probe_*.py              # 결함을 좁힐 때 쓴 측정 도구
    ├── TEST_SCENARIO.md        # 전체 시나리오 테스트의 설계 문서
    ├── requirements.txt
    └── test_*.py (73개)        # 아래 "테스트 항목 개요" 표 참고
```

---

## 사전 요구사항

- Python 3.10+ (`pip install -r tests/requirements.txt`)
- Godot 4.7 실행 파일 — 자동화가 이걸로 게임을 직접 띄웁니다
- 대상 게임 프로젝트 — 경로는 환경변수 `GODOT_EXE` / `GAME_PROJECT` 로 지정 (격리용 APPDATA 는 `AUTOTEST_APPDATA`)
- (폰 실기로 돌릴 때만) Android SDK Platform-Tools(`adb`)와 USB 디버깅이 켜진 실기기

---

## 실행 방법

**현재 제공하는 건 PC(엔진)에서 돌리는 방법입니다.** 자동화가 Godot 로 게임을 직접 띄우므로 폰이 없어도 전부 돌아갑니다. 진입점은 `tests/run_all.py` 하나:

```
python tests/run_all.py                     # 전부: unit → integration → server → full (몇 시간)
python tests/run_all.py --quick             # unit 만 (헤드리스, 약 5분)
python tests/run_all.py --stages unit,server    # 원하는 단계만
python tests/run_all.py --resume            # 이전에 통과한 단계는 건너뛰고, full 은 끝까지 통과한 곡도 건너뜀
python tests/run_all.py --cleanup           # server 단계 뒤 장부에 적힌 테스트 데이터를 실제로 삭제 (없으면 목록만)
```

- 단계: `unit`(마커 no_server 전부) · `integration`(게임 창 필요, `--no-server`) · `server`(개발 서버에 그대로 접속) · `full`(`test_full_scenario.py`, 마지막에 게임 종료).
- **앞 단계가 실패해도 끝까지 돈다.** 끝에 단계별 합계 표가 나오고 `tests/reports/full_run_state.json`에 남는다. 결과 파일은 실행마다 새로 생기는 결과 폴더에 모인다(아래 "테스트 결과").
- 이어하기: `--resume`이면 통과한 단계는 건너뛴다. `full`은 곡마다 끝까지 통과하면 `tests/reports/full_scenario_progress.json`에 적어 두었다가 다음에 그 곡을 건너뛴다(건너뛴 곡은 엑셀에 N/A로 남는다). `--resume` 없이 돌리면 진행 기록을 비우고 처음부터 돈다.
- 최근 전체 실행(2026-11-10 22:03 ~ 11-11 00:25, 2시간 22분): **1,623건 실패 0** — unit 1,361 · integration 202 · server 43 · full 17. 결과 폴더는 `tests/reports/2026_11_10_1/`(결과물은 저장소에 올리지 않는다).

### 폰 실기로 돌릴 때 (참고)

`1_install_and_launch.bat`(APK 설치 + `adb forward tcp:5000` + 앱 실행) → `2_run_tests.bat`(기본 스위트, 앱을 안 끔) → `3_run_full_scenario.bat`(전체 시나리오, 마지막에 앱 종료) 순서입니다. 같은 테스트가 폰에서도 그대로 돕니다.

다만 **디버그 APK 는 이 저장소에 올리지 않으므로**(아래 "테스트 대상 앱") 받은 그대로는 1번을 돌릴 수 없습니다.

---

## 테스트 결과

**풀 테스트(`run_all.py`)** 는 실행할 때마다 `tests/reports/yyyy_mm_dd_차수` 폴더(차수는 그날 몇 번째 실행인지, 숫자만)를 새로 만들고 그 안에 결과를 모읍니다 (2026-11-11). 이어하기(`--resume`)는 이전 실행의 폴더를 그대로 씁니다.

| 파일 | 내용 |
|----|------|
| `TC_결과.xlsx` | 사람이 읽는 테스트 케이스 형식. `요약` 시트(대분류별 PASS/FAIL/N/A)와 `TC` 시트(TC 번호·대분류·중분류·소분류·사전 조건·테스트 절차·순번·기대 결과·결과·비고·자동화 시험 이름). 풀 테스트가 끝나면 `tests/tc_export.py`가 자동으로 만든다. 케이스 문장은 `tests/tc_catalog/*.json`에 있고, 새 시험을 만들면 여기에 문장을 같이 써야 한다(없으면 뽑지 않고 빠진 시험 이름을 알려 준다). 2026-11-10 실행 기준 **2,542줄**(PASS 2,513 · N/A 29) |
| `test_results.xlsx` | 시험 이름 그대로의 결과(단계마다 시트) |
| `FAIL_*.png` | 실패한 시험의 스크린샷(통과한 시험은 찍지 않는다) |
| `run_log.txt` | 실행 로그 |
| `full_run_state.json` | 단계별 통과/실패 요약 |
| `full_run_<단계>.xml` | 단계별 pytest 결과 |

**시험 파일을 따로 돌릴 때**(`pytest test_xxx.py`)는 폴더를 만들지 않고 `tests/reports/test_results.xlsx`에 기록됩니다. 실행할 때마다 파일은 누적되고,
`일-월-년도` 이름의 새 시트가 추가됩니다 (같은 날 재실행 시 `(2)`, `(3)`... 붙음).

| 열 | 내용 |
|----|------|
| Test Number | 세부 항목 번호 |
| Test Case | 테스트 항목명 |
| Result | PASS / FAIL / SKIP / N/A |
| Note | 판정값 상세 또는 실패 사유 |
| Screenshot | 실패 시 캡처된 스크린샷 이미지가 셀에 직접 삽입됨 |

`N/A` 항목은 자동화하지 않는 영역(계정·외부 로그인, 모양, 사용성, 폰 전용 동작)으로 `test_na_user_areas.py` 25개이며, 비고란에 "유저 테스트 필요"와 자동화되는 앞부분의 시험 이름이 기록됩니다. `--resume`으로 건너뛴 곡도 N/A 로 남습니다.

---

## 테스트 항목 개요

시험 파일 **73개**입니다. 단계로 나누면 계산·데이터 1,361 · 게임 화면 202 · 서버 43 · 전체 시나리오 17 (2026-11-10 실행 기준).

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
| `test_unit_records.py` | **모듈 13** (2026-11-08) — 로컬 기록 저장(`RecordLocalStore`·`RecordService`): 첫 기록은 음수여도 저장, 같거나 낮으면 거부, 높으면 시퀀스·레인믹스 로그까지 교체, 곡·난이도·플랫폼·계정별 분리, 최근 플레이, 전체 삭제, 서버 없는 상태, song_id 규칙 |
| `test_songselect.py` | **곡 선택 화면 21개** — 곡 목록(채보 파일에서 읽은 기대값), 이름순/난이도순/최근 정렬과 방향·저장, 키 수·난이도 버튼의 "가장 가까운 조합" 규칙(24번 눌러 모델과 비교), 배속 ±0.25·곡별 저장·0.25~10 한계, 저사양/노트 랜덤/목표 등급 저장, UCC 준비중, PLAY·뒤로 |
| `test_rival_screens.py` | Best Score·라이벌 탭, 라이벌 관리 팝업, 전체 리더보드를 서버 없이 확인(8개) |
| `test_server_screens.py` | 서버 데이터가 있을 때 — 1위 표시, 리더보드 줄(순위·닉네임·달성률·등급·날짜), 라이벌 R 표시와 등록/해제 확인 창, 관리 팝업 등록·해제·오류 문구(자기 자신·없는 닉네임·6번째), 라이벌 탭 ◀▶, 고스트 드롭다운(7개, `server`) |
| `test_settings.py` | **설정 화면 16개** — 탭 4개, 닉네임 팝업(미리 채움·취소·오류·변경 후 복원), 오디오 오프셋, 언어·테마 드롭다운과 저장, 사운드 4줄(슬라이더·퍼센트·끄기 접힘·±5%), 이퀄라이저 10밴드, 크레딧 라이선스 팝업 |
| `test_server_settings.py` | 로그인한 계정의 설정 — 로그아웃·탈퇴 버튼, 확인 창 취소, 로그아웃 뒤 새 게스트 세션(장부에 적음). 탈퇴는 실행하지 않음(4개, `server`) |
| `test_server_config.py` | 서버 `app_config` 값이 게임 `RemoteConfig`에 그대로 반영되는지, 없는 키는 꺼짐(2개, `server`) |
| `test_mainmenu.py` | 메인 메뉴 캐러셀 9개 — 타일 글자·준비중 표시, 화살표/스와이프/가운데 터치로 이동·진입, 짧은 드래그 무시, 뒤로가기 경고 |
| `test_boot.py` | 부팅 5개 — 회사 로고(글자 없음, 연출 약 4.8초 뒤 자동 이동, 터치로 스킵), 타이틀('화면을 눌러 시작'), 터치로 메인 메뉴, 뒤로가기 경고 |
| `test_gameplay_ui.py` | 게임 플레이 화면 9개 — 시작 카운트다운 3·2·1, AUTO·게이지·콤보·판정 글자, 일시정지 창(배속·오프셋·버튼)과 콤보 정지, 배속 한계, 오프셋 슬라이더 저장, 재개 카운트다운, 뒤로가기 키, 곡 선택으로 |
| `test_autoplay_target_grade.py` | 디버그 자동 플레이 목표 등급 7개(S++~D) — 무작위 곡을 전부 쳐서 Miss·Oops 0, 콤보 유지, 결과 등급이 목표와 같음 (2026-11-09 자동 플레이 버그 수정 확인) |
| `test_judgment_display.py` | 입력을 넣었을 때 WOW·GREAT·GOOD·OOPS·MISS 판정 글자가 플레이 화면에 뜨는지(무작위 곡, `/debug_judge_note`로 곡 시계 기준 입력) |
| `test_target_grade_hud.py` | 플레이 중 목표 등급 줄(이름·ME·점수 차이) 8개(MAX~D) — 차이가 `내 EX − 커트라인×3×판정된 노트 수` 규칙대로인지(무작위 곡) |
| `test_lanemix_prompt.py` | 플레이 중 레인믹스 안내 2개(무작위 곡) — TAP 수락 → READY → 3·2·1 → 키 수 전환 → 원복 3·2·1, 안 누르면 그대로 |
| `test_ghost_hud.py` | 플레이 중 고스트 3개(`server`, ARTCORE 4K EZ) — BEST/RIVAL·ME·점수 차이, 목표 등급 줄 |
| `test_result_screen.py` | 결과 화면 24개 — 실제 자동 플레이 한 판의 숫자(EX·달성률·콤보·판정 개수)를 게임 계산값과 대조, 등급 그림 9종·마크 그림 8종(경로), 다시 하기·곡 선택 |
| `test_english_screens.py` | 영어로 돌렸을 때 모든 화면(타이틀·메인 메뉴·설정 4탭·곡 선택·팝업·리더보드·결과·튜토리얼 전 대사·일시정지)에 한글이 안 남았는지(10개, 테마 이름은 2026-11-10부터 번역 키라 설정 탭 전부에서 한글 없음 확인) |
| `test_lanemix_boundary.py` | 레인믹스 구간 시작·끝 경계 입력 소실 15판 (2026-11-10) — 보정이 양수라 입력 시각이 구간 시작을 넘어도 눌린 노트가 전부 판정되는지(수정 전 11실패). 곡·키 수·난이도·보정·오차를 바꿔 한 판에 오차 하나로 누름. 느림 |
| `test_lanemix_end_layout.py` | 레인믹스 구간 끝 직후 노트 배치 튐 (2026-11-10) — CITY POP 4K EZ에서 구간 끝 이후 기본 노트가 처음 보일 때부터 기본 키 수 배치인지(수정 전 5키로 보여 실패) |
| `test_tutorial_layout.py` | 튜토리얼 4단계 노트 배치 튐 (2026-11-10) — 단계 시각·구간 끝에서 어떤 노트도 처음 보인 뒤 그려진 x가 바뀌지 않는지 |
| `test_miss_calibration.py` | Miss 확정이 판정과 같은 보정을 쓰는지 (2026-11-10) — 보정 −100/+100/0에서 늦은 Great·Good·Oops는 판정되고 Oops 창(250ms)을 넘으면 Miss. 서버 없음 |
| `test_resume_keys.py` | 풀 시나리오 이어하기 키 (2026-11-08) — 채보 파일 내용이 바뀌면 키가 달라져 그 곡을 다시 도는지(게임·서버 없이, `no_server`) |
| `test_server_score.py` | 서버 검증 10개 (`server`) — 기록 저장·서버 점수 재계산(submit_score)·조작 거부(노트 수 불일치·미등록 채보)·마크·닉네임. 서버 DB는 읽기 전용으로 직접 조회, 시험용 채보(notetest_*)만 사용 |
| `test_server_social.py` | 서버 검증 5개 (`server`) — 라이벌 등록·해제·제한, 클라이언트 리더보드 조회(순위·닉네임), 고스트 시퀀스 접근 권한. 게임의 `LeaderboardService`를 `/debug_service`로 호출 |
| `test_data_assets.py` | 데이터 검증 118개 (2026-11-10, 파일만 읽음) — 효과음 26종(코드의 `SFX_NAMES`와 파일·임포트가 일치, 형식·무음·길이), 메뉴 BGM 8종(60초 이하·루프), 도트 폰트 5종(임포트 설정 보존)·OFL 라이선스, 그림 PNG 전부(유효·임포트됨)·런처 아이콘 크기 |
| `test_debug_ui_split.py` | 개발용/릴리스용 분리 3개 (2026-11-10) — 게임을 두 번 띄워 인자 없이는 DEBUG 버튼·F키 안내·FPS 글자가 보이고 `--hide-debug`에서는 숨겨지며 AUTO 표시는 남는지. 릴리스 APK에서의 `OS.is_debug_build()` 분기는 PC에서 못 봄 |
| `test_unit_slide.py` | **모듈 (슬라이드)** 9개 — 슬라이드 장면·방향 값 저장·홀드형 아님. 방향은 판정에 안 쓰임 — 방향 판정은 쓸 예정이나 구현 보류(사용자 결정, DESIGN §7) |
| `test_replay.py` | 리플레이 재생 1개 (2026-11-10) — 목표 B 자동 플레이 한 판 뒤 같은 판을 리플레이로 열어 점수·판정 개수·최대 콤보·등급이 같고 기록을 다시 저장하지 않는지. 시험이 찾은 결함(레인믹스 구간 시작 시각의 기본 노트에 기록이 하나 더 쓰여 밀림, TASK_LIST #34-1)을 같은 날 고침. 측정 도구 `probe_replay_miss.py` |
| `test_song_preview.py` | 곡 미리듣기 1개 — 곡을 고르면 미리듣기 재생기가 켜져 위치가 앞으로 가고, 그동안 곡 선택 BGM이 줄어들고, 끝나면 하나로 돌아와 음량이 복귀하며 다시 재생되지 않음 |
| `test_unit_upload_queue.py` | **모듈 14** 오프라인 업로드 큐 (2026-11-10) — 같은 곡·난이도·플랫폼은 높은 점수 하나만 남김, 다시 보낼 때 통신 실패만 큐에 남기고 영구 실패·성공은 뺌, `--no-server`에서 남음, 손상된 파일 |
| `test_unit_package.py` | **모듈 15** 곡 패키지(.rgz) (2026-11-10) — 경로 조작 엔트리 거부 4종, song_uid 폴더·병합 규칙(manifest 유지·음원 스킵·같은 이름 다른 내용은 chart_uid 이름으로 보존), 진짜 공식 서명 잠금과 서명 없는 패키지 거부·격리, 변조 패키지 |
| `test_server_functions.py` | 서버 함수 2개 (`server`, 2026-11-10) — 게임이 부르는 `link_google_play`는 인증 코드가 비면 400 `missing_auth_code`(구글에 닿기 전 거부), 디버그 엔드포인트의 함수 허용 목록(게임이 부르는 `submit_score`·`link_google_play`만). 서버에 쓰지 않는 호출만 |
| `test_unit_palette.py` | **모듈 16** 비주얼 테마 3종 팔레트 (2026-11-10) — 테마 ID·경로·표시 이름, 키빔 모드 3종, 판정 이펙트 5등급 설정, 노트 색 흰/파랑 순서(4·5·6·8·16키), 마크 8종, 등급·게이지 색 조회, 불투명 색, 연출 규모가 Wow > Great > Good 순(길이·입자 수; 종류는 같아도 됨, DESIGN §11) |
| `test_data_palette.py` | astral_ocean 파일에 직접 적힌 색 65개가 도트 팔레트 30색 안인지(DESIGN §13-3, 다른 두 테마는 대상 아님), 테마 파일 3개 형식 (3개, 파일만 읽음) |
| `test_unit_fileutil.py` | **모듈 17** 원자적 파일 저장 (2026-11-10) — 새 파일·덮어쓰기·한글·20만 글자, 끝난 뒤 `.tmp` 없음, 임시파일을 못 열거나 폴더가 없을 때 오류 코드를 돌려주고 기존 파일 내용이 그대로 남음 |
| `test_unit_audiobus.py` | **모듈 18** 오디오 버스 적용 — 버스 4개, 선형→dB, 음소거, 이퀄라이저 자동 프리앰프·켜고 끄기, 키음 재생 음량 |
| `test_unit_ghost.py` | **모듈 19** 라이벌/전일 1위 고스트 진행 계산 — 누적 EX 표, 시점 조회 경계, 최대 EX, 중도 종료 기록, 빈 시퀀스 |
| `test_unit_chartloader.py` | **모듈 20** 채보 불러오기 보조 — meta만 읽기가 전체 읽기와 채보 70개 전부에서 같음, 특이한 파일, 곡 폴더 자켓·풀믹스·미리듣기 찾기 17곡, manifest, 접근자 기본값 |
| `test_unit_clock.py` | **모듈 21** 곡 시계와 보정 — 음수 시작·일시정지 고정·재개 이어가기·정지, 보정 ±200 자르기·저장·복원, 총 지연 |
| `test_unit_settings.py` | **모듈 22** 게임 설정 — 볼륨 4종·음소거·이퀄라이저 자르기, 곡별 배속, 저장→다시 읽기 복원, S-RANDOM 읽을 때 없음, 잘못된 이퀄라이저 저장값 방어 |
| `test_unit_keysound.py` | **모듈 23** 키음 불러오기 — sounds 전부 등록, 빈 항목·없는 파일 제외, 상대 경로, 확장자 폴백(.ogg→.wav), 스트림 읽기 |
| `test_unit_authurl.py` | **모듈 24** 로그인 연동 보조 — 인증 주소 만들기(인코딩), "이미 연결됨" 오류 판별 |
| `test_unit_popups.py` | **모듈 25** 공용 팝업 — ErrorPopup·ConfirmPopup·ProtoNoticePopup 글자·버튼·콜백·물리 뒤로가기·동의 저장 |
| `test_unit_userservice.py` | **모듈 26** 유저 프로필·닉네임 — 표시폭(한글 2)·허용 글자·게스트 로컬 저장·프로필 복원·게스트 로그아웃/탈퇴 |
| `test_error_popups.py` | 게임 시작 오류 팝업 3개 (2026-11-10, 전에는 "재현 어려우면 PASS") — 채보 파일 없음·깨진 채보·키음 없음 → 오류 팝업 → 확인 시 곡 선택 |
| `test_orientation_flip.py` | 화면 뒤집힘 감지 → 자동 일시정지 4개 — 처음 값은 기준만, 애매한 값 무시, 부호 반전 시 정지, 정지 중 재반전은 쌓이지 않음 (`/debug_gravity`로 센서 값 주입) |
| `test_low_spec_play.py` | 저사양 모드 재생 경로 — 켜고 풀믹스가 있는 곡을 치면 풀믹스 경로가 켜지고 끄면 꺼짐 |
| `test_song_list_drag.py` | 곡 목록 끌어서 스크롤 5개 (2026-11-10) — 위로 끌면 목록이 내려가고 곡 선택은 안 바뀜, 아래로 끌면 올라가 맨 위에서 멈춤, 계속 끌면 목록 끝에서 멈춤, 목록 밖에서 시작한 끌기 무시, 임계값 아래 움직임은 탭 (`/debug_drag`·`/debug_scroll`) |
| `test_na_user_areas.py` | **N/A 항목 25개 (비고 "유저 테스트 필요")** — 계정·외부 로그인 5(탈퇴 실행·Play Games·PC 구글 로그인·구글 연동 복구·라이벌 탈퇴 알림), 모양 9, 사용성 6, 폰 전용 5. 각 비고에 자동화로 확인되는 앞부분의 시험 이름도 적음. 결과 엑셀에 N/A 로 남음 |
| `test_server_leaderboard_ext.py` | 서버 9개 (`server`, 2026-11-10) — 전일 1위 조회(순위·닉네임·점수·등급, 기록 없는 곡은 빈 값), 실패 기록 판별, 라이벌 기록 조회, 라이벌 알림 조회·삭제 호출, 계정 복구(로컬을 비우고 서버 기록 내려받기), 서버 시퀀스 리플레이(전일 1위·라이벌의 판정을 그대로 재생, 기록 저장 안 함) |
| `COVERAGE.md` | **시험 범위 대조표** — 게임 스크립트 80개·데이터·서버 함수를 시험과 하나씩 대조(시험/화면/모양/폰·외부/안 씀/빈 곳). 점검 도구 `tests/coverage_audit.py` |

### 단위 테스트(헤드리스) 구조

```
godot_unit/run_unit.gd        # 실행기: --headless --script 로 unit_<모듈>.gd 를 불러 @@UNIT@@ 줄로 결과 출력
godot_unit/unit_balance.gd    # 모듈 1 본체 (기대값은 DESIGN.md 수치를 직접 적음)
godot_unit/unit_selfcheck.gd  # 자체 점검: 메모리의 수치를 잠깐 바꿔 테스트가 변경을 잡는지 확인(게임 파일은 안 건드림)
godot_unit/unit_lanes.gd      # 모듈 2 본체 / unit_selfcheck_lanes.gd 는 모듈 2의 자체 점검
godot_unit/unit_upload_queue.gd · unit_package.gd · unit_palette.gd · unit_slide.gd · unit_fileutil.gd · unit_audiobus.gd · unit_ghost.gd · unit_chartloader.gd · unit_clock.gd · unit_settings.gd · unit_keysound.gd · unit_authurl.gd · unit_popups.gd · unit_userservice.gd   # 모듈 14~26·슬라이드 본체 (2026-11-10)
godot_unit/unit_timing.gd     # 모듈 3 본체 / unit_lanemix.gd 는 모듈 4 본체 (모듈 3·4는 바꿀 수 있는 전역 수치가 없어 자체 점검 없음 — 기대값을 손계산으로 적음)
tests/godot_runner.py         # Python 래퍼 (Godot 경로·게임 프로젝트·격리 APPDATA는 환경변수 GODOT_EXE / GAME_PROJECT / AUTOTEST_APPDATA 로 변경)
tests/test_unit_balance.py    # 항목 하나 = pytest 케이스 하나, 기존 엑셀 리포트에 같이 기록
```

- 실행: `cd tests` 후 `pytest test_unit_balance.py test_unit_lanes.py test_unit_timing.py test_unit_lanemix.py` (기기 연결 불필요, 모듈마다 5~20초). 모듈이 스크립트 오류로 멈추면 실행기의 감시 타이머가 90초 뒤 오류 원문과 함께 끝낸다.
- 서버 없이 도는 테스트는 `@pytest.mark.no_server` 표시를 달면 TestServer 연결 확인과 실패 스크린샷 시도를 건너뜁니다.
- 명세와 코드가 다른데 어느 쪽이 맞는지 정해지지 않은 항목은 `test_unit_balance.py`의 `KNOWN_ISSUES`에 사유와 함께 올려 두고 xfail로 표시합니다(통과해 버리면 오히려 실패로 알려 줍니다).
- **모듈이 스크립트 오류로 중간에 끝나면 검사가 조용히 빠진다** (2026-11-08 모듈 2에서 발견: 터치 구역·터치 입력 검사 40건이 뷰포트 null 오류로 만들어지지 않았는데 "통과"로 보고됨). 그래서 `run_unit_module`은 엔진의 `SCRIPT ERROR`를 모아 모듈마다 `스크립트 오류 없음` TC를 추가하고, 예상된 오류만 `allow_errors`로 허용한다. 뷰포트·오토로드 `_ready`가 필요한 모듈은 `var needs_frames := true`를 두면 실행기가 프레임 2번을 기다린 뒤 시작한다(`--no-server`가 항상 붙어 서버에는 접속하지 않음).
- **서버 접속 금지 (2026-11-07 사고 이후)**: 게임을 그냥 띄우면 오토로드 `SupabaseHTTP._ready()`가 `ensure_session()`으로 **개발 서버에 익명 계정을 만들고**, 오토플레이로 치면 기록도 올라간다. 그래서 자동화에서 게임을 띄울 때는 반드시 `godot_runner.start_game()`을 쓴다. 이 함수는 기본으로 엔진 인자 `--no-server`를 붙이고(끄는 건 서버 접속 테스트용 `allow_server=True` 하나뿐, 아래 참조) APPDATA도 격리한다. `--no-server`는 디버그 빌드에서만 동작하며 서버로 나가는 모든 요청을 막는다. 단위 테스트(헤드리스)는 프레임을 기다리지 않아 서버에 접속하지 않는다(실행 후 격리 폴더에 `supabase_session.json`이 없어야 정상). `tests/test_no_server.py`가 이 효과(세션 파일 미생성, 서버 호출 차단, 외부 TCP 연결 0개)를 확인한다.
- **헤드리스 실행기도 항상 `--no-server`를 붙인다** (2026-11-08 사고: 모듈이 스크립트 오류로 멈춰 감시 타이머 전까지 프레임이 돌았고, 그동안 오토로드 `_ready`가 개발 서버에 익명 계정을 만들었다). 모듈 5가 이 가드를 확인한다.
- **게임 창이 필요한 통합 테스트는 게임을 자동으로 띄운다** (2026-11-08): 세션 시작 때 포트 5000에 10초 동안 응답이 없으면 `conftest.py`가 `start_game()`(항상 `--no-server`)으로 PC에서 게임을 직접 띄우고 세션이 끝나면 종료한다. 폰 등 이미 떠 있는 게임이 있으면 그것을 쓴다. 끄려면 환경변수 `AUTOTEST_AUTOLAUNCH=0`(그러면 게임이 없을 때 skip). 확인: 기존 통합 18개(`test_flow`·`test_autoplay`·`test_marks`·`test_best_record`) 전부 통과(13분 19초), `supabase_session.json` 미생성.
- **서버 접속 테스트만 예외 (2026-11-08, 사용자 확정)**: 기록 저장·서버 점수 재계산·리더보드·라이벌·닉네임은 서버가 있어야 검증된다. 이런 테스트에는 `@pytest.mark.server`를 단다(개발 서버에 그대로 접속한다). 서버 테스트는 맨 뒤로 정렬되고, 그때 게임을 `--no-server` 없이 서버 전용 APPDATA(`tests/reports/_appdata_server`, 로그인 세션이 실행 사이에 남음)로 다시 띄운다(`start_game(allow_server=True)`). 서버에 만든 계정은 만드는 즉시 장부 `server_ledger.jsonl`(저장소 루트, 추적 안 함)에 적는다(`tests/server_ledger.py`). 정리는 `python tests/cleanup_server.py` — **장부에 적힌 계정만** 대상이고, 기본은 지울 목록·행 수만 보여준다(읽기 전용). 익명 계정은 계정째, 고정 테스트 계정(`debug_test_account{N}`)은 계정·닉네임을 남기고 기록 행만 지운다. 장부 밖 의심 계정은 보여주기만 한다. 실제 삭제는 `--apply`이고 사용자 확인 뒤에만 실행한다(Supabase CLI가 이 프로젝트를 production으로 표시하고 쓰기에는 `--yes`를 요구한다). 규칙 검사: `tests/test_server_ledger.py`.
- **화면에 보이는 글자로 확인하는 테스트 — 튜토리얼·처음 실행 (2026-11-08)**: 게임 TestServer의 `GET /screen_texts`(지금 화면에 보이는 Label·Button·입력창 글자, 아이콘 버튼은 안쪽 라벨), `POST /screen_press?text=`(글자로 버튼 누르기), `POST /screen_input?text=`(입력창 채우기), `POST /debug_profile?key=&value=`(프로필 값 바꾸기, 예: `tutorial_seen=false`)를 쓴다(`client.screen()`·`press_text()`·`fill_input()`, 공용 도구는 `tests/screen_helpers.py`). `test_tutorial.py`(23개)는 첫 화면·이전/다음·단계별 대사·START·자동 시연·예/아니오·완료·스킵·BGM 이어짐·설정 다시보기를, `test_onboarding.py`(7개)는 빈 프로필로 처음 켠 뒤 로그인 화면→게스트 경고→닉네임 팝업→닉네임 검사→메인 메뉴→첫 PLAY가 튜토리얼인 것까지를 확인한다. 후자는 마커 `fresh_profile`이라 게임을 빈 프로필로 새로 띄운다. 시험용 프로필은 언어를 한국어로 고정하고, 닉네임·튜토리얼·온보딩 완료 표시를 미리 적어 둔다(처음 실행 테스트만 빈 프로필). 튜토리얼 대사는 `docs/TUTORIAL_SPEC.md` §4 표를 `screen_helpers.DIALOGUE`에 따로 옮겨 놓고 화면과 비교하며, 줄바꿈 위치는 비교하지 않는다. 소리·모양은 사람이 확인한다.
- **전 화면 글자 확인에 쓰는 TestServer 훅 (2026-11-08)**: 위 3종에 더해 `GET /screen_texts` 항목에 탭 제목(`tab`)·슬라이더 값/투명도(`slider`)·그림 경로(`image`)·버튼 안쪽 글자(`inner`)가 들어간다. 조작은 `POST /screen_option?n=&item=`(n번째 드롭다운 항목 고르기), `/screen_tab?text=`(탭 옮기기), `/screen_slider?n=&value=`(슬라이더 값), `/screen_press_nth?n=`(글자 없는 아이콘 버튼), `/back`(안드로이드 뒤로가기 키), `/navigate/company_logo`, `/debug_click?...&no_release=1`/`&release_only=1`(스와이프). 체크·토글 버튼은 누르면 상태까지 뒤집힌다. 모두 디버그 빌드의 127.0.0.1 전용이며 릴리스 내보내기는 `debug/*`를 제외한다.
- 게임 사용자 폴더(`%APPDATA%\RhythmGame_New`)와 서버 세션을 건드리지 않도록 게임 프로세스에만 `APPDATA`를 `tests/reports/_appdata`로 바꿔 줍니다.

자세한 시나리오 설계(법칙, 케이스별 상태)는 [`tests/TEST_SCENARIO.md`](tests/TEST_SCENARIO.md) 참고.

---

## 자동화가 찾은 결함 (예시)

시험을 만드는 과정에서 나온 것 중 두 건입니다. 둘 다 시험에서 우회하지 않고 게임 쪽을 고친 뒤 같은 시험으로 다시 확인했습니다.

| 증상 | 어떻게 잡았나 | 조치 |
|---|---|---|
| 결과 화면에서 리플레이를 열면 **직전 판이 아닌 이전 판**이 재생됨 | `test_replay.py` — 자동 플레이 한 판의 점수·판정 개수·최대 콤보·등급을 리플레이와 대조 | 레인믹스 구간 시작 시각의 기본 노트에 기록이 한 번 더 쓰여 한 칸씩 밀리던 것을 수정 |
| 계정 복구 뒤 서버 기록을 받으면 **남의 최고 기록이 내 로컬 기록으로 저장**됨 | `test_server_leaderboard_ext.py` — 로컬을 비우고 서버 기록을 내려받은 뒤 저장된 기록의 주인 확인 | 기록 표가 SELECT 공개라 조회 두 곳에 내 아이디(`user_id`) 조건을 추가 |

시험의 목적은 통과율이 아니라 결함을 찾는 것이므로, 실패를 지우거나 통과시키지 않습니다. 시간 초과처럼 외부 요인으로 보이는 실패도 정해진 횟수(서버 로그인은 3회)만 다시 시도하고, 그래도 안 되면 FAIL 로 기록하며 다시 시도해 성공한 횟수를 함께 남깁니다.

---

## 테스트 대상 앱

대상 게임은 **ASTRAL RAIN** (Godot 4.7 / Android) 이고, 2026-11-05 itch.io 에 프로토타입을 공개했습니다 — <https://vaiaaaaaa.itch.io/astral-rain>

- 수록 17곡 × 4난이도(EZ·NM·HD·EX), 4·5·6·8키, 레인믹스, 서버 리더보드·라이벌·고스트·리플레이
- 플랫폼: Android (개발 기준 해상도 2400 × 1080)
- 테스트 서버 포트: 5000 — **디버그 빌드에서만** 켜지고 127.0.0.1 전용. 릴리스 내보내기는 `debug/*` 를 제외합니다
- **빌드(APK)는 이 저장소에 올리지 않습니다** — 디버그 빌드에는 시험 계정 정보가 들어갈 수 있어 `.gitignore` 에서 `apk/`·`*.apk`·`*.aab` 를 전부 제외합니다
