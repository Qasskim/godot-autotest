# -*- coding: utf-8 -*-
"""화면에 보이는 글자로 확인하는 테스트용 공용 도구 (튜토리얼·온보딩).

- ui(키): 게임의 한국어 문구(strings.csv ko 열). 버튼·팝업 이름을 하드코딩하지 않고 같은 문구로 찾는다.
- 튜토리얼 대사는 docs/TUTORIAL_SPEC.md §4 표(사용자가 직접 다듬은 최종본)를 그대로 옮긴 것이다. 게임의 로케일 파일과 따로 적어 두어서 문구가 바뀌면 잡힌다.
"""
import csv
import os
import time

import client
from godot_runner import GAME_PROJECT

_STRINGS: dict = {}


def ui(key: str) -> str:
    if not _STRINGS:
        with open(os.path.join(GAME_PROJECT, "locale", "strings.csv"), encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        ko = rows[0].index("ko")
        for r in rows[1:]:
            if r:
                _STRINGS[r[0]] = r[ko]
    return _STRINGS[key]


# docs/TUTORIAL_SPEC.md §4 — 스테이지별 대사 (스테이지 0~4 = 화면의 Stage 1~5)
DIALOGUE = [
    ["어서 와요! 만나서 반가워요.",
     "그럼, 간단한 튜토리얼부터 시작해볼게요.",
     "먼저, 네 가지 노트를 알아볼게요.",
     "TAP — 판정선에 닿는 순간, 한 번 눌러주세요.",
     "LONG — 누른 채로 노트가 끝날 때까지 유지해주세요.",
     "SLIDE — 화살표가 가리키는 방향으로 슬라이드해주세요.",
     "DRAG — 표시된 궤적을 따라 움직여주세요."],
    ["노트를 누른 타이밍에 따라 판정이 달라져요.",
     "WOW가 가장 정확한 판정이고, GREAT와 GOOD이 이어져요.",
     "너무 빠르거나 늦으면 OOPS, 놓치면 MISS예요.",
     "그럼 노트 다섯 개로 각 판정을 직접 확인해볼게요."],
    ["화면 아래에 이런 안내가 나타날 때가 있어요. 레인믹스 안내예요.",
     "가운데 버튼을 누르면 준비가 되고, 3, 2, 1 카운트다운 뒤에 레인믹스에 진입해요. 누르지 않으면 지금 레인 그대로 이어져요.",
     "레인믹스를 실행할지는 여러분이 직접 선택할 수 있어요.",
     "레인믹스가 끝날 때도 3, 2, 1 카운트다운 뒤에 원래대로 돌아와요."],
    ["좋아요! 이제 직접 레인믹스를 시작해볼게요.",
     "4키로 시작해서, 버튼을 누르면 레인이 점점 늘어나요."],
    ["좋아요! 기본 레인믹스를 완료했어요.",
     "이번에는 무작위 레인믹스를 경험해볼까요?",
     "여기까지 게임의 기본 플레이를 모두 알아봤어요.",
     "튜토리얼은 설정에서 언제든 다시 플레이할 수 있어요. 튜토리얼 완료를 축하합니다!!"],
]
STAGE_TITLES = ["기본 노트", "판정 등급", "레인믹스 안내", "레인믹스 모드 체험", "실전 체험"]
HAS_START = [True, True, False, True, False]      # 노트가 있어 마지막 대사에서 START가 나오는 단계(YES/NO 단계는 따로)


def norm(text: str) -> str:
    """줄바꿈·연속 공백을 한 칸 공백으로 — 게임은 긴 대사를 중간에 줄바꿈해서 보여 주지만 사양서 표에는 한 줄로 적혀 있다. 줄바꿈 위치는 비교하지 않는다."""
    return " ".join(text.split())


def labels() -> list:
    """화면에 보이는 글자(Label)를 줄바꿈 없이 정리한 목록."""
    return [norm(t) for t in client.screen_labels()]


def labels_and_inner() -> list:
    """화면 글자 + 버튼 안쪽에 얹힌 글자(리더보드 줄처럼 줄 전체가 버튼인 경우의 칸 글자)를 줄바꿈 없이 정리한 목록."""
    out = labels()
    for i in client.screen()["items"]:
        if i["kind"] == "button":
            out += [norm(t) for t in i.get("inner", [])]
    return out


def stage_label(stage: int) -> str:
    return norm(f"Stage {stage + 1}\n{STAGE_TITLES[stage]}")


def wait_until(cond, timeout: float = 15.0, interval: float = 0.3) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(interval)
    return cond()


def press(text: str) -> None:
    assert client.press_text(text), f"화면에 '{text}' 버튼이 보이지 않습니다 — 보이는 버튼: {client.screen_buttons()}"
    time.sleep(0.25)


def dialogue_now() -> str:
    """튜토리얼 화면의 대사 한 줄 — 'Stage' 표시와 판정 글자(AUTO PLAY 등)를 뺀 글자."""
    found = [t for t in labels() if not t.startswith("Stage ")]
    return found[0] if found else ""


def enter_tutorial_via_play() -> None:
    """튜토리얼을 아직 안 본 상태로 만들고 MainMenu 에서 PLAY 를 눌러 들어간다(처음 설치 후 첫 PLAY 와 같은 경로)."""
    client._req("POST", "/debug_profile?key=tutorial_seen&value=false")
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15), "MainMenu 전환 실패"
    time.sleep(0.8)
    client.tap_mainmenu_play()
    assert client.wait_for_scene("Tutorial", timeout=10), "PLAY 를 눌렀는데 튜토리얼이 열리지 않았습니다"
    time.sleep(0.8)


def enter_tutorial_via_settings() -> None:
    """설정의 '튜토리얼 다시보기' 로 들어간다(스테이지 선택 팝업이 뜨는 경로)."""
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15), "MainMenu 전환 실패"
    time.sleep(0.8)
    client.tap_mainmenu_settings()
    assert client.wait_for_scene("Settings", timeout=10), "설정 화면이 열리지 않았습니다"
    time.sleep(0.5)
    client._req("POST", "/tap/settings_tutorial_open")
    assert client.wait_for_scene("Tutorial", timeout=10), "튜토리얼 다시보기를 눌렀는데 튜토리얼이 열리지 않았습니다"
    time.sleep(0.8)


def jump_to_stage(stage: int, line: int = 0) -> None:
    """튜토리얼 안에서 단계 앞으로 이동(스테이지 선택 훅) 후 line 번째 대사까지 '다음'을 눌러 간다."""
    client._req("POST", f"/tap/tutorial_picker_stage?index={stage}")
    time.sleep(0.4)
    for _ in range(line):
        press(ui("tutorial_next_btn"))
