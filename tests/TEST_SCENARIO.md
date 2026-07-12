# 테스트 시나리오 (풀 자동화 — 포트폴리오용 인스턴트 라운드)

> 이 시나리오는 [project_test_scenario_workflow] 워크플로우에 따른 법칙 기반으로 작성됨.
> 서버(Firebase) 작업 전 예외처리 정의 선행 과제와는 별개 트랙.

## 법칙

1. 모든 화면에서 FAIL 발생 시 스크린샷 + 설명을 남긴다.
2. 구현된 모든 화면에 진입해야 한다. 단, 예외 팝업은 재현이 안 되면 현재는 PASS 처리 가능.
3. 구현된 모든 버튼 및 기능에 대한 테스트 진행 필요.
4. 큰 흐름: 게임 실행 → 메인화면 → 설정화면 → 곡 선택 화면 → 곡 플레이 화면 → 리절트 화면 → [모든 채보 테스트할 때까지 반복] → 완료 후 정상종료 시도 → 결과 저장.

## 확정된 세부 규칙 (질의응답으로 확정)

| 항목 | 결정 |
|------|------|
| TestServer.gd/DebugState.gd 엔드포인트 확장 | 진행 — 버튼별 신호/엔드포인트 신규 추가 |
| 포즈 오버레이(배속/캘리브레이션 슬라이더/재개/나가기) | 채보마다 반복 테스트, 매번 다른 임의 값 사용 |
| MainMenu QUIT 버튼 | 전체 시나리오 맨 마지막 1회만 (법칙 4의 "정상종료 시도"와 동일) |
| FAIL 기록 형식 | xlsx Note 컬럼에 스크린샷 경로 텍스트 + 셀에 이미지 직접 삽입, 둘 다 |
| 곡 폴더 선택(FileDialog/Android 오버레이) | **N/A 처리** — 비고: "세부 기획 및 구현 중" (케이스는 남겨두되 실행 안 함) |
| 채보 목록 확보 방법 | **고정값/사전 캐싱 절대 금지.** 테스트 실행 시점마다 SongSelect 화면 진입 직후 `GET /songs`로 그 화면이 실제 렌더링한 목록(개수/순서)을 그 자리에서 라이브 조회 → 1번부터 N번까지 순서대로 실제 탭(`tap/song_at?index=N`)해서 진입. 화면에 뜨는 것과 다른 값을 절대 미리 갖고 있으면 안 됨 |

---

## 전체 케이스 목록

### 0. 앱 실행
| 케이스 | 방법 | 상태 |
|--------|------|------|
| 서버 응답 확인 | `GET /ping` | ✅ 기존 |
| MainMenu 진입 확인 | `GET /scene` == "MainMenu" | ✅ 기존 |

### 1. MainMenu
| 케이스 | 방법 | 상태 |
|--------|------|------|
| Play 버튼 클릭 → SongSelect | 🔧 신규: `POST /tap/mainmenu_play` (실제 버튼 신호 발생, 기존 `navigate/song_select`는 씬 강제전환이라 버튼 자체 검증 아님) | 🔧 신규 |
| Settings 버튼 클릭 → Settings 화면 | 🔧 신규: `POST /tap/mainmenu_settings` | 🔧 신규 |
| 뒤로가기 2회 종료 경고 토스트 | 🔧 신규: `POST /back` (WM_GO_BACK_REQUEST 시뮬레이션) 2회 호출 후 토스트 노출 간접 확인(스크린샷) | 🔧 신규 |
| QUIT 버튼 → 정상 종료 | 🔧 신규: `POST /tap/mainmenu_quit` | 🔧 신규, **시나리오 맨 마지막 1회만** |

### 2. Settings
| 케이스 | 방법 | 상태 |
|--------|------|------|
| 뒤로가기 버튼 → MainMenu | 🔧 신규: `POST /tap/settings_back` | 🔧 신규 |
| 캘리브레이션 팝업 열기 | 🔧 신규: `POST /tap/settings_calibrate_open` | 🔧 신규 |
| TAP 버튼 8회 입력 | 🔧 신규: `POST /tap/settings_calibrate_tap` ×8 | 🔧 신규 |
| 재시도 버튼 | 🔧 신규: `POST /tap/settings_calibrate_retry` | 🔧 신규 |
| 적용 버튼 | 🔧 신규: `POST /tap/settings_calibrate_apply` | 🔧 신규 |
| 닫기 버튼 | 🔧 신규: `POST /tap/settings_calibrate_close` | 🔧 신규 |
| 곡 폴더 선택 (FileDialog / Android 오버레이) | — | **N/A — 세부 기획 및 구현 중** |

### 3. SongSelect
| 케이스 | 방법 | 상태 |
|--------|------|------|
| 전일 기록 탭 전환 | 🔧 신규: `POST /tap/songselect_tab_world` | 🔧 신규 |
| 내 기록 탭 전환 | 🔧 신규: `POST /tap/songselect_tab_my` | 🔧 신규 |
| 라이벌 탭 전환 | 🔧 신규: `POST /tap/songselect_tab_rival` | 🔧 신규 (Phase 2 미구현이라 "라이벌 없음" 상태 확인이 전부) |
| 디버그 팝업 열기/닫기 | 🔧 신규: `POST /tap/songselect_debug_open`, `.../songselect_debug_close` | 🔧 신규 (팝업 내부 오토플레이/등급/터치존 토글은 기존 `/autoplay`, `/autoremix` + 신규 `/touchzone` 엔드포인트로 이미 커버) |
| 뒤로가기 → MainMenu | 🔧 신규: `POST /tap/songselect_back` | 🔧 신규 |
| 곡 목록 라이브 조회 | 🔧 신규: `GET /songs` — 진입 시점마다 화면이 실제 렌더링한 목록을 그 자리에서 반환 (캐싱 없음) | 🔧 신규 |
| N번째 곡 선택 + Play → GameScene | 🔧 신규: `POST /tap/song_at?index=N` (인덱스 기반 실제 탭) + `tap/play` | 🔧 신규 (기존 `tap/first_song`은 0번 고정이라 전체 순회엔 부족) |

### 4. GameScene (채보마다 반복)
| 케이스 | 방법 | 상태 |
|--------|------|------|
| 카운트다운 → 오토플레이 진행 → 종료 감지 | `wait_game_finished()` | ✅ 기존 |
| 포즈 오버레이 열기 | 🔧 신규: `POST /tap/pause_open` | 🔧 신규 |
| 배속 조절 (±, 임의 값) | 🔧 신규: `POST /tap/pause_speed_up`, `.../pause_speed_down` | 🔧 신규 |
| 캘리브레이션 슬라이더 (임의 값) | 🔧 신규: `POST /pause/calibration?value=N` | 🔧 신규 |
| 재개 버튼 | 🔧 신규: `POST /tap/pause_resume` | 🔧 신규 |
| 나가기 버튼 → SongSelect | 🔧 신규: `POST /tap/pause_quit` (채보 1개는 이 경로로, 나머지는 완주로 분기) | 🔧 신규 |
| 터치존 오버레이 표시 | 🔧 신규: `POST /touchzone/on`, `/touchzone/off` | 🔧 신규 |
| 마크 리빌 오버레이 | `/result`의 marks 필드로 간접 검증 | ✅ 기존 (화면 직접 확인 아님, 스크린샷과 병행 권장) |
| 채보 로드 실패 팝업 | 재현 어려우면 Pass | ⚠️ 법칙 2 적용 |
| 음악 파일 누락 팝업 | 재현 어려우면 Pass | ⚠️ 법칙 2 적용 |

### 5. ResultScreen (채보마다 반복)
| 케이스 | 방법 | 상태 |
|--------|------|------|
| 점수/정확도/등급/마크 표시 | `GET /result` | ✅ 기존 |
| 기록 저장 실패 팝업 | 재현 어려우면 Pass | ⚠️ 법칙 2 적용 |
| 재시도 버튼 | `tap/retry` | ✅ 기존 |
| 곡선택으로 버튼 | `tap/select_song` | ✅ 기존 |

### 6. 반복 종료 후
| 케이스 | 방법 | 상태 |
|--------|------|------|
| `GET /songs` 전체 순회 완료 확인 | 순회 카운터 == 곡 개수 | 🔧 신규 (위 `/songs` 기반) |
| MainMenu 이동 후 QUIT → 정상 종료 | `tap/mainmenu_quit`, 프로세스 종료 확인 | 🔧 신규, 맨 마지막 1회 |

### 7. 결과 저장
| 항목 | 방법 |
|------|------|
| xlsx 시트 누적 (일-월-년도) | ✅ 기존 (`result_writer.py`) |
| FAIL 시 스크린샷 저장 + 경로 텍스트 | 🔧 확장 필요 (현재는 성공 케이스만 일부 스크린샷) |
| FAIL 시 스크린샷 셀에 이미지 삽입 | 🔧 신규 (`openpyxl.drawing.image.Image`) |

---

## 구현 필요 항목 요약

**Godot 쪽 (`Godot/debug/TestServer.gd`, `Godot/debug/DebugState.gd`, 각 UI 스크립트에 신호 연결):**
- MainMenu: play, settings, quit 버튼 신호 3개 + 뒤로가기 시뮬레이션
- Settings: back, calibrate open/tap/retry/apply/close 신호 6개
- SongSelect: tab world/my/rival, debug open/close, back 신호 6개 + `GET /songs`(라이브 목록 조회) + `POST /tap/song_at?index=N`(인덱스 기반 탭)
- GameHUD(Pause): open, speed up/down, calibration slider(값 지정), resume, quit 신호 6개
- GameScene: touchzone on/off 신호 2개

**Python 쪽 (`tests/`):**
- `client.py`에 위 엔드포인트 대응 함수 추가
- 전체 채보 순회 루프 (곡 목록 기반 파라미터화 테스트)
- FAIL 발생 시 자동 스크린샷 캡처 + xlsx Note 컬럼 경로 기록 (conftest.py 훅 확장)
- `result_writer.py`에 이미지 삽입 기능 추가 (`openpyxl.drawing.image.Image`)

---

> 마지막 업데이트: 2026-07-13 (구현 완료 — `tests/test_full_scenario.py` + `Godot/debug/TestServer.gd`·`DebugState.gd` 엔드포인트 25개 반영. Godot 실행 후 실제 PASS 흐름 확인은 아직 안 됨)
