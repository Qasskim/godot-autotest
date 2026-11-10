# -*- coding: utf-8 -*-
"""비주얼 테마 팔레트 파일 — astral_ocean 이 도트 팔레트 30색만 쓰는지 (기준 DESIGN §13-3 "palette_astral_ocean.tres만 이 색으로 맞춤", 2026-11-10).

파일 글자만 읽는다(Godot·서버 불필요). 파일에 직접 적힌 모든 Color(...)(마크 색 딕셔너리·판정 이펙트 하위 리소스 포함)의 RGB 가 30색 안에 있어야 한다.
적히지 않은 필드는 스크립트 기본값을 물려받는 것이 설계라(DESIGN §11) 검사하지 않는다. 다른 두 테마(cosmic_neon·abyss_ether)는 이 색 제한 대상이 아니다.
30색은 DESIGN §13-3 의 목록을 그대로 옮긴 것이다.
"""
import os
import re

import pytest
from godot_runner import GAME_PROJECT

pytestmark = pytest.mark.no_server

DOT_PALETTE_30 = """010112 0a1623 0f2a44 023c54 0b5f7a 1f5055 348a87 1fd8c9 5effeb bffff7
0f3d61 14659f 1a99f2 4cd9ff b8e8ff 000000 14181f 6b7280 b3b3b3 ffffff
ff3333 ff8033 ffd91a 4dff66 ab87ff 022551 024372 025169 033048 031d42""".split()
PALETTE_DIR = os.path.join(GAME_PROJECT, "resources", "palette")


def colors(path: str) -> list:
    text = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"Color\(([^)]*)\)", text):
        r, g, b, a = [float(x) for x in m.group(1).split(",")]
        out.append(("#%02x%02x%02x" % tuple(round(v * 255) for v in (r, g, b)), a))
    return out


def test_dot_palette_has_exactly_30_distinct_colors():
    assert len(DOT_PALETTE_30) == 30 and len(set(DOT_PALETTE_30)) == 30


def test_astral_ocean_uses_only_the_30_color_dot_palette():
    cols = colors(os.path.join(PALETTE_DIR, "palette_astral_ocean.tres"))
    assert len(cols) > 30, f"색을 거의 못 읽었습니다({len(cols)}개) — 파일 형식이 바뀌었는지 확인"
    outside = sorted({c for c, _ in cols if c[1:] not in DOT_PALETTE_30})
    assert not outside, f"도트 팔레트 30색 밖의 색이 파일에 적혀 있습니다: {outside}"


def test_every_theme_file_exists_and_is_a_gameplay_palette():
    for theme in ("astral_ocean", "cosmic_neon", "abyss_ether"):
        text = open(os.path.join(PALETTE_DIR, f"palette_{theme}.tres"), encoding="utf-8").read()
        assert 'script_class="GameplayPalette"' in text or "GameplayPalette.gd" in text, f"{theme}: GameplayPalette 리소스가 아닙니다"
        assert f'theme_id = "{theme}"' in text, f"{theme}: theme_id 줄이 없습니다"
