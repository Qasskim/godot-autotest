# 시험 범위 대조표 — 아스트랄 레인(게임 기능·데이터)

> 2026-11-10 작성. 게임 스크립트 80개·씬·데이터·서버 함수를 하나씩 대조했다. 점검 도구: `tests/coverage_audit.py`(스크립트 이름·공개 함수 이름이 시험에 나오는지 셈). 이 도구는 **이름이 나오는지**만 보며 줄 단위 실행 범위는 아니다(Godot에는 GDScript 줄 단위 측정 도구가 없음).
>
> **풀 테스트의 범위(사용자 정의, 2026-11-10)**: 게임의 기능 및 데이터 중 Claude가 자동화할 수 있는 만큼. 모양·사용성·폰 전용 동작은 시험 목록(TC)에 N/A 항목으로 남기고 비고에 "유저 테스트 필요"를 적는다(`tests/test_na_user_areas.py`).
>
> 분류(표의 "모양"·"폰·외부"는 모두 TC 에 N/A, 비고 "유저 테스트 필요"로 있음): **시험** = 그 코드를 직접 확인하는 시험이 있음 / **화면** = 화면·엔진 시험이 그 동작을 거쳐 확인 / **모양** = 눈으로 보는 것(범위 밖) / **폰·외부** = 폰 센서·Play Games·외부 로그인(범위 밖) / **안 씀** = 쓰는 곳이 없는 코드 / **빈 곳** = 시험이 없어 만들어야 함

## 1. 스크립트 80개

| 스크립트 | 분류 | 확인하는 시험 / 비고 |
|---|---|---|
| audio/AudioManager | 시험 | test_unit_audiobus(버스·음량·음소거·이퀄라이저·키음 음량), test_unit_audio, test_unit_settings |
| audio/BgmPlayer | 화면 | test_song_preview(미리듣기·음량 복귀), test_tutorial(BGM 이어짐) |
| audio/KeySoundManager | 시험 | test_unit_keysound, test_unit_audio(pan) |
| chart/BMSLoader | 안 씀 | 어디서도 부르지 않음(참조 없음) |
| chart/ChartLoader | 시험 | test_unit_chartloader, test_unit_package, test_unit_signing, test_data_charts |
| chart/ChartManager | 화면 | 모든 플레이·튜토리얼 시험이 채보를 불러옴 |
| core/ChartTiming | 시험 | test_unit_timing, test_unit_scroll |
| core/ComboSystem·GaugeSystem·JudgmentSystem·ScoreSystem·GameBalance | 시험 | test_unit_balance |
| core/FileUtil | 시험 | test_unit_fileutil |
| core/GameManager | 화면 | test_autoplay*, marks, judgment_display, lanemix_*, miss_calibration, replay, target_grade_hud, ghost_hud, gameplay_ui, result_screen, error_popups, orientation_flip, low_spec_play |
| core/GameSettings | 시험 | test_unit_settings, test_settings, test_songselect |
| core/GameplayPalette·JudgmentTierConfig·PaletteManager | 시험 | test_unit_palette, test_data_palette |
| core/GoogleOAuthPC | N/A | PC 브라우저 구글 로그인 — 유저 테스트 영역(test_na_user_areas) |
| core/LaneGuides | 모양 | 레인 배경선·키 하이라이트 |
| core/LaneMixEntry·LaneMixState·NoteRandomizer | 시험 | test_unit_lanemix, test_lanemix_prompt, test_lanemix_boundary, test_lanemix_end_layout |
| core/LaneSystem | 시험 | test_unit_lanes |
| core/LeaderboardService | 시험 | test_server_social, test_server_screens, test_server_leaderboard_ext(전일 1위·라이벌 기록·실패 기록 판별·알림 확인). 라이벌 탈퇴 알림 생성은 실계정 탈퇴가 필요해 N/A(유저 테스트 영역) |
| core/Locale | 시험 | test_unit_locale, test_data_locale, test_english_screens |
| core/MusicPlayer | 시험 | test_unit_clock |
| core/RecordLocalStore·RecordService | 시험 | test_unit_records, test_best_record, test_server_score |
| core/RecordSupabaseSync | 시험 | test_unit_upload_queue, test_server_score |
| core/RemoteConfig | 화면 | test_server_config |
| core/RivalGhostSystem | 시험 | test_unit_ghost, test_ghost_hud |
| core/SceneManager | 화면 | 모든 화면 전환 시험, test_debug_ui_split(`--hide-debug`) |
| core/ScreenLayout | 시험 | test_unit_scroll(11개 해상도 레이아웃·폰트 규칙) |
| core/SupabaseHTTP | 시험 | test_unit_offline(`--no-server` 차단), test_unit_authurl. 토큰 갱신·PKCE 교환은 외부 로그인이 필요해 N/A(유저 테스트 영역) |
| core/TimeSignature | 시험 | test_unit_timing |
| core/TimingManager | 시험 | test_unit_timing, test_unit_clock |
| core/ToastManager | 화면 | 종료 경고 토스트(test_mainmenu, test_boot) |
| core/UserService | 시험 | test_unit_userservice, test_onboarding, test_server_settings, test_server_score(닉네임) |
| effects/HoldEffect·JudgmentEffect·LaneMixTransition | 모양 | 판정 연출의 길이·입자 수 순서는 test_unit_palette |
| input/InputManager | 시험 | test_unit_lanes |
| notes/DragNoteVisual | 시험 | test_unit_drag |
| notes/LongNoteVisual | 시험 | test_unit_hold |
| notes/NotePositionCalculator | 시험 | test_unit_scroll |
| notes/SlideNoteVisual | 시험 | test_unit_slide(현재 동작 고정; 방향 판정은 보류 — 사용자 결정, DESIGN §7) |
| notes/LaneMixTriggerNote | 안 씀 | 옛 트리거 노트(안내 버튼 방식으로 대체됨, DESIGN §9). `LaneMixState.find_active_trigger`만 참조 |
| notes/LaneRenderer·MeasureLineRenderer·NoteBase·NoteFieldClip·TapNoteVisual | 모양 | 레인 그룹 경계는 test_unit_lanes, 노트 키 수 배치는 test_lanemix_end_layout |
| notes/TutorialLaneMixDemoNote | 모양 | 튜토리얼 3단계 설명용 그림 |
| ui/CompanyLogo·TitleScreen | 화면 | test_boot |
| ui/ConfirmPopup·ErrorPopup·ProtoNoticePopup | 시험 | test_unit_popups, test_error_popups(채보 로드 실패·키음 없음) |
| ui/DragScrollContainer | 시험 | test_song_list_drag(끌어서 스크롤·곡 선택 안 바뀜·맨 위/끝 멈춤·목록 밖 시작 무시·임계값 아래는 탭) |
| ui/ExitOnDoubleBack | 화면 | test_mainmenu, test_boot(뒤로가기 경고) |
| ui/FoldContainer | 화면 | test_settings(사운드 줄 접힘) |
| ui/GameHUD | 화면 | test_gameplay_ui, test_target_grade_hud, test_ghost_hud, test_result_screen. 모양(마크 연출·번쩍임)은 범위 밖 |
| ui/IconTextButton·MarqueeLabel·ModalShell·PixelStyleBox·ReleaseOptionButton·WedgeGauge | 모양 | 버튼·라벨·게이지 그리기 |
| ui/LaneMixPrompt | 화면 | test_lanemix_prompt |
| ui/Leaderboard | 화면 | test_rival_screens, test_server_screens |
| ui/LoginScreen·NicknameGate | 화면 | test_onboarding, test_server_settings |
| ui/MainMenu | 화면 | test_mainmenu |
| ui/ResultScreen | 화면 | test_result_screen |
| ui/Settings | 화면 | test_settings, test_server_settings |
| ui/SongSelect | 화면 | test_songselect, test_server_screens |
| ui/Tutorial·TutorialBackdrop·TutorialGameplay | 화면 | test_tutorial, test_tutorial_layout, test_onboarding |

## 2. 데이터

| 데이터 | 분류 | 시험 |
|---|---|---|
| 수록 채보 68개 + 튜토리얼 채보 구조·메타·노트·타이밍·레인믹스 | 시험 | test_data_charts, test_unit_chartloader(meta만 읽기 = 전체 읽기) |
| 곡 폴더(manifest·풀믹스·미리듣기·자켓) | 시험 | test_data_charts, test_unit_chartloader(찾기 함수) |
| 공식 채보 서명 | 시험 | test_unit_signing |
| 번역(ko/en) | 시험 | test_data_locale, test_unit_locale, test_english_screens |
| 효과음 26종·BGM 8종·폰트 5종·그림 PNG·런처 아이콘 | 시험 | test_data_assets |
| 비주얼 테마 3종(팔레트) | 시험 | test_unit_palette, test_data_palette(아스트랄 오션 30색) |
| 사용자 설정·프로필·로컬 기록·업로드 큐 | 시험 | test_unit_settings, test_unit_userservice, test_unit_records, test_unit_upload_queue |
| 곡 패키지(.rgz) | 시험 | test_unit_package |
| 서버 점수 재계산·리더보드·라이벌·관리자 전용 함수 거부 | 시험 | test_server_score, test_server_social, test_server_screens, test_server_functions |

## 3. 시험하지 않는 것 (N/A — 유저 테스트 필요)

사용자 지시(2026-11-10): 계정·외부 로그인, 모양, 사용성, 폰 전용 동작은 시험 항목(TC)만 만들고 N/A 로 두며 비고에 "유저 테스트 필요"를 적는다. 항목 25개는 `tests/test_na_user_areas.py`(계정·외부 로그인 5, 모양 9, 사용성 6, 폰 전용 5). 각 항목의 비고에 자동화로 확인되는 앞부분이 어느 시험인지 함께 적혀 있다.

아래 표는 그중 계정·외부 로그인 5개다.

| 항목 | 비고 |
|---|---|
| 계정 탈퇴 실행(`delete_account`) | N/A, 유저 테스트 필요. 탈퇴 버튼과 확인 창 취소까지는 test_server_settings |
| Google Play Games 로그인 성공 | N/A, 유저 테스트 필요. 로그인 화면 버튼·게스트 경고는 test_onboarding |
| PC 구글 로그인 성공(`GoogleOAuthPC`) | N/A, 유저 테스트 필요. 인증 주소·오류 판별은 test_unit_authurl |
| 구글 계정 연동 성공·계정 복구(`link_google_play` 성공) | N/A, 유저 테스트 필요. 인증 코드 없는 호출 거부는 test_server_functions |
| 라이벌 탈퇴 알림 생성 | 라이벌이 실계정을 탈퇴해야 생겨서 N/A. 알림 조회·삭제 호출은 test_server_leaderboard_ext |

**게임이 부르는 서버 함수**: `add_rival`·`delete_account`·`link_google_play`·`register_nickname`·`remove_rival`·`submit_score` 6개. 게임 디버그 서버의 함수 호출 허용 목록은 이 중 `submit_score`·`link_google_play`만이다.

## 4. 사용자 결정 대기·보류

- 슬라이드 방향 판정: 보류(DESIGN §7). 판정 연출: 지금 구현에 맞춰 정리함(DESIGN §11).
- 알려진 결함 없음(리플레이 기록 밀림은 2026-11-10 수정, TASK_LIST #34).
- 위 N/A 외에 범위 안에서 시험이 없는 항목: 없음(이 문서를 쓴 시점).
