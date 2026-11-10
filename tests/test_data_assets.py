# -*- coding: utf-8 -*-
"""데이터 검증 — 효과음·메뉴 BGM·폰트·그림 파일 (기준 DESIGN §12 오디오 버스, §13-2 도트 폰트, §13-3 도트 BGM/효과음, 2026-11-10).

파일만 읽는다(읽기 전용, Godot·서버 불필요). 소리는 들어 보지 않고(사람 몫) 파일이 있는지, 형식이 읽히는지, 무음이 아닌지, 길이가 설계 범위인지,
임포트 설정(루프·글꼴 안티앨리어싱)이 설계대로인지 본다.
이 시험의 값(효과음 길이 상한 10초)은 사용자가 정한 값이 아니라 시험 작성자가 정했다(수록 효과음 중 가장 긴 것이 4.2초). BGM 60초 이하·루프는 DESIGN §13-3 문장이다.
"""
import glob
import os
import re
import struct
import wave

import pytest
from godot_runner import GAME_PROJECT

pytestmark = pytest.mark.no_server

SFX_DIR = os.path.join(GAME_PROJECT, "audio", "sfx")
BGM_DIR = os.path.join(GAME_PROJECT, "audio", "bgm")
BGM_NAMES = ["bgm_title", "bgm_mode_select", "bgm_settings", "bgm_free", "bgm_arcade", "bgm_course", "bgm_tutorial_explain", "bgm_tutorial_practice"]   # DESIGN §13-3
FONT_DIR = os.path.join(GAME_PROJECT, "assets", "fonts", "galmuri")
FONT_FILES = ["Galmuri7.ttf", "Galmuri9.ttf", "Galmuri11.ttf", "Galmuri11-Bold.ttf", "Galmuri14.ttf"]   # DESIGN §13-2
SFX_MAX_SECONDS = 10.0


def sfx_names() -> list:
    """AudioManager.SFX_NAMES 를 코드에서 그대로 읽는다(시험이 이름을 따로 갖고 있지 않게)."""
    text = open(os.path.join(GAME_PROJECT, "scripts", "audio", "AudioManager.gd"), encoding="utf-8").read()
    block = re.search(r"const SFX_NAMES[^=]*=\s*\[(.*?)\n\]", text, re.S).group(1)
    return re.findall(r'"([a-z_0-9]+)"', re.sub(r"#.*", "", block))


def import_text(path: str) -> str:
    return open(path + ".import", encoding="utf-8").read()


def ogg_info(path: str) -> dict:
    data = open(path, "rb").read()
    assert data[:4] == b"OggS", f"{path}: Ogg 파일이 아닙니다"
    i = data.find(b"\x01vorbis")
    assert i >= 0, f"{path}: Vorbis 헤더가 없습니다"
    channels = data[i + 11]
    rate = struct.unpack("<I", data[i + 12:i + 16])[0]
    last = data.rfind(b"OggS")
    granule = struct.unpack("<q", data[last + 6:last + 14])[0]
    return {"channels": channels, "rate": rate, "seconds": granule / rate}


# ── 효과음 ──────────────────────────────────────────────────────────

def test_sfx_names_in_code_have_no_duplicates():
    names = sfx_names()
    assert len(names) == len(set(names)), f"SFX_NAMES 에 중복이 있습니다: {names}"
    assert len(names) > 0


@pytest.mark.parametrize("name", sfx_names())
def test_sfx_file_exists_is_readable_not_silent_and_short(name):
    path = os.path.join(SFX_DIR, name + ".wav")
    assert os.path.isfile(path), f"효과음 파일이 없습니다: {path}"
    assert os.path.isfile(path + ".import"), f"임포트 파일이 없습니다(에디터에서 한 번 열지 않았음): {name}.wav.import"
    with wave.open(path, "rb") as w:
        n, ch, width, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        frames = w.readframes(n)
    assert ch in (1, 2) and width == 2 and rate > 0, f"{name}: 채널 {ch}, 비트 {width * 8}, 샘플레이트 {rate}"
    seconds = n / rate
    assert 0 < seconds <= SFX_MAX_SECONDS, f"{name}: 길이 {seconds:.2f}초"
    samples = struct.unpack("<%dh" % (len(frames) // 2), frames)
    assert max(abs(s) for s in samples) > 0, f"{name}: 완전한 무음 파일입니다"


def test_no_sfx_file_without_a_name_in_code():
    on_disk = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(SFX_DIR, "*.wav"))}
    extra = sorted(on_disk - set(sfx_names()))
    assert not extra, f"코드(SFX_NAMES)에 없는 효과음 파일이 있습니다(쓰이지 않거나 이름 누락): {extra}"


# ── 메뉴 BGM ────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", BGM_NAMES)
def test_bgm_file_is_ogg_within_60_seconds_and_loops(name):
    path = os.path.join(BGM_DIR, name + ".ogg")
    assert os.path.isfile(path), f"BGM 파일이 없습니다: {path}"
    info = ogg_info(path)
    assert info["channels"] in (1, 2), info
    assert 0 < info["seconds"] <= 60, f"{name}: 길이 {info['seconds']:.1f}초 (DESIGN §13-3: 60초 이하)"
    assert "loop=true" in import_text(path), f"{name}: 임포트 설정이 루프가 아닙니다(DESIGN §13-3: 무한 루프)"


def test_no_bgm_file_outside_the_documented_eight():
    on_disk = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(BGM_DIR, "*.ogg"))}
    assert on_disk == set(BGM_NAMES), f"DESIGN §13-3 의 8곡과 다릅니다 — 더 있음 {sorted(on_disk - set(BGM_NAMES))} / 없음 {sorted(set(BGM_NAMES) - on_disk)}"


# ── 도트 폰트 ───────────────────────────────────────────────────────

@pytest.mark.parametrize("name", FONT_FILES)
def test_pixel_font_exists_and_import_keeps_dots_sharp(name):
    path = os.path.join(FONT_DIR, name)
    assert os.path.isfile(path) and os.path.getsize(path) > 0, f"폰트가 없습니다: {path}"
    head = open(path, "rb").read(4)
    assert head in (b"\x00\x01\x00\x00", b"true", b"OTTO"), f"{name}: 글꼴 파일 머리가 이상합니다 {head!r}"
    text = import_text(path)
    for want in ("antialiasing=0", "hinting=0", "subpixel_positioning=0"):
        assert want in text, f"{name}: 임포트 설정에 {want} 가 없습니다(DESIGN §13-2: 도트가 번지지 않게 바꾸지 말 것)"


def test_font_license_text_is_kept():
    assert os.path.isfile(os.path.join(FONT_DIR, "OFL_LICENSE_Galmuri.txt")), "OFL 라이선스 텍스트가 없습니다(DESIGN §13-2 의무)"


# ── 그림 ────────────────────────────────────────────────────────────

def png_size(path: str) -> tuple:
    head = open(path, "rb").read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path}: PNG 가 아닙니다"
    return struct.unpack(">II", head[16:24])


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(GAME_PROJECT, "assets", "**", "*.png"), recursive=True)),
                         ids=lambda p: os.path.relpath(p, os.path.join(GAME_PROJECT, "assets")).replace("\\", "/"))
def test_every_asset_png_is_valid_and_imported(path):
    w, h = png_size(path)
    assert w > 0 and h > 0, f"{path}: 크기 {w}x{h}"
    assert os.path.isfile(path + ".import"), f"임포트 파일이 없습니다(에디터에서 한 번 열지 않았음): {os.path.basename(path)}.import"


def test_launcher_icons_have_the_sizes_in_their_names():
    base = os.path.join(GAME_PROJECT, "assets", "branding")
    for name, size in (("android_main_192.png", 192), ("android_adaptive_bg_432.png", 432), ("android_adaptive_fg_432.png", 432), ("android_adaptive_mono_432.png", 432)):
        assert png_size(os.path.join(base, name)) == (size, size), f"{name} 크기가 이름과 다릅니다"
