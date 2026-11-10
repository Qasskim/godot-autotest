# -*- coding: utf-8 -*-
"""유저 테스트 영역 — 자동화하지 않는 게임 기능을 시험 목록(TC)에 N/A 로 남긴다 (2026-11-10, 사용자 지시 "TC에 테스트 케이스 추가하고 N/A처리하고 비고란에 유저 테스트 필요로 코멘트").

세 갈래다. 결과 엑셀(test_results.xlsx)에 N/A 와 비고가 기록되고, 실제 확인은 사람(이 게임을 체험한 외부 사용자 포함)이 한다.
  1) 계정·외부 로그인: 실계정이 지워지거나 외부(구글) 계정이 필요한 동작
  2) 모양·사용성: 눈과 손과 귀로 판단하는 것(그려진 모양, 연출, 반응감, 소리)
  3) 폰 전용 동작: 폰에서만 일어나거나 폰에서만 의미가 있는 것
각 항목의 비고에는 자동화로 확인되는 앞부분(논리·수식·글자·상태)이 어느 시험인지 함께 적는다. 항목은 현재 게임에 있는 기능만 적었다.
"""
import pytest

from conftest import record_na

pytestmark = pytest.mark.no_server

NOTE = "유저 테스트 필요"

CASES = [
    # ── 1) 계정·외부 로그인 ──
    ("설정: 계정 탈퇴 실행 (UserService.delete_account → delete_account 함수, 서버 기록·시퀀스·라이벌 완전 삭제 후 새 게스트 세션)",
     NOTE + " — 계정/외부 로그인. 실계정이 지워지는 동작이라 실행하지 않음. 탈퇴 버튼과 확인 창 취소까지는 test_server_settings."),
    ("로그인: Google Play Games 로그인 성공 (Android, PlayGamesSignInClient)",
     NOTE + " — 계정/외부 로그인. 폰과 구글 계정 필요. 로그인 화면 버튼·게스트 경고는 test_onboarding."),
    ("로그인: PC 구글 로그인 성공 (GoogleOAuthPC, 브라우저 인증 후 PKCE 코드 교환)",
     NOTE + " — 계정/외부 로그인. 브라우저와 구글 계정 필요. 인증 주소·'이미 연결됨' 오류 판별은 test_unit_authurl."),
    ("로그인: 구글 계정 연동 성공과 계정 복구 (link_google_play 성공, 로그아웃 뒤 재연동으로 기록 복원)",
     NOTE + " — 계정/외부 로그인. 구글 인증 코드 필요. 인증 코드 없는 호출 거부는 test_server_functions, 기록 내려받기는 test_server_leaderboard_ext."),
    ("리더보드: 라이벌 탈퇴 알림 생성 (delete_account 가 남기는 1회성 안내 → 곡 선택에서 확인 팝업)",
     NOTE + " — 계정/외부 로그인. 라이벌이 실계정을 탈퇴해야 생김. 알림 조회·삭제 호출은 test_server_leaderboard_ext."),

    # ── 2) 모양 ──
    ("모양: 탭·롱·드래그·슬라이드 노트의 그려진 모양과 색",
     NOTE + " — 모양. 흰/파랑 색 순서 데이터는 test_unit_palette, 노트 키 수 배치는 test_lanemix_end_layout."),
    ("모양: 레인 배경·판정선·키빔·마디선·중앙선",
     NOTE + " — 모양. 레인 그룹 경계 계산은 test_unit_lanes."),
    ("모양: 판정 이펙트(Wow·Great·Good·Oops·Miss)의 연출과 등급별 구별감, 홀드 이펙트",
     NOTE + " — 모양. 연출 설정값(길이·입자 수 순서)은 test_unit_palette."),
    ("모양: 레인믹스 전환 연출(번쩍임, 키 수가 바뀔 때 레인 보간 애니메이션, 미리보기 선)",
     NOTE + " — 모양. 전환 시점·키 수·안내 상태는 test_lanemix_prompt, 노트 배치는 test_lanemix_end_layout."),
    ("모양: 쐐기형 HP 게이지와 고스트 게이지의 그려진 모양·색",
     NOTE + " — 모양. 게이지 값은 test_unit_balance, 고스트 점수 차이 글자는 test_ghost_hud."),
    ("모양: 마크 연출(풀콤보 등 마크 공개)과 결과 화면 등급 그래프(물결선 포함)",
     NOTE + " — 모양. 마크·등급 그림 경로와 숫자는 test_result_screen."),
    ("모양: 비주얼 테마 3종(astral_ocean·cosmic_neon·abyss_ether)의 색감과 구별",
     NOTE + " — 모양. 색 필드·30색 제한·노트 색 순서는 test_unit_palette, test_data_palette."),
    ("모양: 도트 폰트·UI 박스·버튼·팝업의 그려진 모양과 화면비별 겹침·잘림",
     NOTE + " — 모양. 레이아웃 수식과 글자 크기 규칙은 test_unit_scroll, 글자 내용은 화면 시험들."),
    ("모양: 회사 로고 도트 전환 애니메이션, 타이틀·메인 메뉴·곡 선택 자켓의 표시",
     NOTE + " — 모양. 연출 시간·화면 이동은 test_boot, 자켓 파일은 test_data_assets."),

    # ── 3) 사용성 ──
    ("사용성: 터치 입력의 반응감과 입력 지연 체감, 판정 보정 슬라이더 체감",
     NOTE + " — 사용성. 보정 부호·Miss 컷·저장은 test_unit_timing, test_miss_calibration, test_unit_clock."),
    ("사용성: 배속 변경 체감과 노트 낙하 가독성",
     NOTE + " — 사용성. 배속 값·저장·범위는 test_songselect, 스크롤 계산은 test_unit_scroll."),
    ("사용성: 곡 목록 끌어서 스크롤의 부드러움·관성",
     NOTE + " — 사용성. 스크롤 동작 자체는 test_song_list_drag."),
    ("사용성: 소리 — 키음·BGM·효과음 음량 균형, 곡 소리 이퀄라이저 체감, 미리듣기·판정·징 소리의 청감",
     NOTE + " — 사용성(청감). 음량 공식·버스 적용·이퀄라이저 값은 test_unit_audio, test_unit_audiobus, 파일 형식은 test_data_assets."),
    ("사용성: 튜토리얼 설명의 이해도와 안내 문구 가독성",
     NOTE + " — 사용성. 대사 내용과 진행은 test_tutorial."),
    ("사용성: 레인믹스 안내(TAP 수락)와 3·2·1 카운트다운을 알아보기 쉬운지",
     NOTE + " — 사용성. 상태 전환은 test_lanemix_prompt."),

    # ── 4) 폰 전용 동작 ──
    ("폰: 화면 자동 회전(뒤집기) 센서의 실제 동작 — Android 에서만 매 프레임 도는 감지",
     NOTE + " — 폰 전용. 감지 논리(부호 반전→자동 일시정지)는 test_orientation_flip."),
    ("폰: 실기기(Galaxy Note 20 등)의 프레임 유지와 저사양 기기 동작",
     NOTE + " — 폰 전용. 저사양 모드의 풀믹스 경로는 test_low_spec_play."),
    ("폰: 물리·제스처 뒤로가기 키와 앱 전환(백그라운드) 뒤 복귀",
     NOTE + " — 폰 전용. 뒤로가기 키 신호 처리는 test_gameplay_ui, test_mainmenu."),
    ("폰: 실기기 화면비·노치·태블릿에서의 배치",
     NOTE + " — 폰 전용. 11개 해상도 레이아웃 수식은 test_unit_scroll."),
    ("폰: 릴리스 APK 에서 개발용 화면(DEBUG 버튼·F키 안내·FPS)이 숨겨지는지, 앱 권한(INTERNET만)",
     NOTE + " — 폰 전용. PC 에서 인자로 숨기는 동작은 test_debug_ui_split(릴리스 빌드 분기 OS.is_debug_build 는 PC 에서 못 봄)."),
]


@pytest.mark.parametrize("case,note", CASES, ids=[f"na_{i:02d}" for i in range(len(CASES))])
def test_na_user_area(case, note):
    record_na(case, note)
    assert True
