# 테스트 자동화

Godot TestServer(포트 5000) 기반 HTTP 테스트.

## 준비

```bash
pip install -r requirements.txt
```

## 실행 전 필수

1. Godot 에디터에서 게임 실행 (디버그 빌드)
2. ADB 포트 포워딩 (Android 실기기인 경우):
   ```bash
   adb forward tcp:5000 tcp:5000
   ```
3. `conftest.py` 상단의 `CHART_PATH`, `MUSIC_PATH`, `SONG_ID`, `DIFFICULTY` 실제 값으로 수정

## 실행

```bash
cd tests

# 전체 실행 (test_full_scenario.py 제외 — 아래 주의 참고)
pytest -v --ignore=test_full_scenario.py

# 빠른 테스트만 (플레이 대기 없는 것)
pytest -v -m "not slow"

# HTML 리포트 생성
pytest -v --html=reports/report.html --self-contained-html

# 특정 파일만
pytest -v test_best_record.py
```

**주의**: `test_full_scenario.py`는 맨 마지막에 MainMenu QUIT 버튼으로 게임을 실제 종료시킨다.
다른 파일과 묶어서 `pytest -v` 로 돌리면 이후 파일이 서버 응답 없음으로 전부 실패하므로
반드시 단독 실행할 것:
```bash
pytest test_full_scenario.py -v
```

## 결과물

- `reports/result_*.png` — 각 테스트의 ResultScreen 스크린샷
- `reports/report.html` — pytest-html 테스트 리포트
- `reports/test_results.xlsx` — 세부 테스트 항목별 PASS/FAIL/SKIP 기록. 파일은 누적, 실행마다 `일-월-년도` 이름의 새 시트 추가 (같은 날 재실행 시 `(2)`, `(3)`... 붙음)

## 테스트 목록

| 파일 | 내용 |
|------|------|
| `test_flow.py` | 씬 전환 플로우 (ping, navigate, 전체 플로우) |
| `test_autoplay.py` | 오토플레이 결과 검증 (점수, 정확도, 판정합계) |
| `test_best_record.py` | 개인 최고기록 갱신/비교 + 스크린샷 |
| `test_marks.py` | 마크 시스템 검증 (perfect/allcombo/allgood/clear/failed) |
| `test_full_scenario.py` | `TEST_SCENARIO.md` 기반 전체 시나리오 — 모든 화면/버튼 진입 + 곡 목록 전체 순회 + 정상종료. **단독 실행 전용** |

## 전체 시나리오 (`test_full_scenario.py`)

`TEST_SCENARIO.md`에 정리된 법칙(모든 화면 진입, 모든 버튼 테스트, FAIL 시 스크린샷, 채보 전체 순회 후 정상종료)을
그대로 구현한 파일. 새로 추가된 디버그 엔드포인트 25개(`Godot/debug/TestServer.gd`, `Godot/debug/DebugState.gd`)를
사용하며, 예외 팝업(채보 로드 실패/음악 누락/기록 저장 실패)과 곡 폴더 선택 기능은 재현이 어렵거나 미구현이라
`N/A` 처리된다(비고: "세부 기획 및 구현 중" 등).
