# -*- coding: utf-8 -*-
"""모듈 7 — 번역 문자열 데이터 검증 (기준: Godot/locale/strings.csv, DESIGN §13의 Locale, 2026-11-05 영어 타이틀 키 노출 사고).

파일만 읽는다(읽기 전용, Godot·서버 불필요). 임포트된 번역이 CSV와 같은지와 Locale 함수 동작은 test_unit_locale.py(Godot 헤드리스)가 본다.
"""
import csv
import glob
import os
import re
from collections import Counter

import pytest
from godot_runner import GAME_PROJECT

pytestmark = pytest.mark.no_server

CSV_PATH = os.path.join(GAME_PROJECT, "locale", "strings.csv")
# 영어 번역이 일부러 비어 있는 키 — 한국어 부제는 영어 화면에 표시하지 않는다(Locale.has로 숨김, 2026-11-05).
INTENTIONALLY_BLANK_EN = {"title_subtitle"}
MARKS = ["perfect", "allcombo", "allgood", "clear", "failed", "straight", "luckyroulette", "evil"]   # DESIGN §5 마크 8종
PLACEHOLDER = re.compile(r"%[-+ 0#]*\d*(?:\.\d+)?[sdif]|\{[a-z_0-9]+\}")
KEY_CALL = re.compile(r"Locale\.(t|tf|t_or|has)\(\s*\"([A-Za-z0-9_]+)\"")


def rows():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def code_files():
    base = GAME_PROJECT
    return glob.glob(os.path.join(base, "scripts", "**", "*.gd"), recursive=True) + glob.glob(os.path.join(base, "debug", "*.gd"))


def used_keys():
    """코드에서 Locale.t/tf/t_or/has에 글자 그대로 넘기는 키 → {(함수, 키): 파일 이름들}."""
    used = {}
    for f in code_files():
        text = open(f, encoding="utf-8").read()
        for m in KEY_CALL.finditer(text):
            used.setdefault((m.group(1), m.group(2)), set()).add(os.path.basename(f))
    return used


def test_csv_header_and_row_shape():
    r = rows()
    assert r[0] == ["keys", "ko", "en"], f"헤더 {r[0]}"
    bad = [i + 1 for i, row in enumerate(r) if len(row) != 3]
    assert not bad and len(r) > 1, f"열 수가 3이 아닌 줄: {bad[:5]}"


def test_keys_unique_and_well_named():
    keys = [row[0] for row in rows()[1:]]
    dup = [k for k, n in Counter(keys).items() if n > 1]
    badname = [k for k in keys if not re.fullmatch(r"[a-z0-9_]+", k)]
    assert not dup and not badname, f"중복 {dup[:5]} / 형식 위반 {badname[:5]}"


def test_no_blank_translations_except_known():
    """한국어는 비어 있으면 안 되고, 영어는 알려진 키(title_subtitle)만 비어 있을 수 있다.
    엔진은 번역이 비면 키 이름을 그대로 화면에 찍는다(2026-11-05 영어 타이틀 사고) — 비는 키는 Locale.has로 숨겨야 한다."""
    r = rows()[1:]
    blank_ko = [row[0] for row in r if not row[1].strip()]
    blank_en = {row[0] for row in r if not row[2].strip()}
    assert not blank_ko, f"한국어가 빈 키 {blank_ko[:5]}"
    assert blank_en <= INTENTIONALLY_BLANK_EN, f"영어가 빈 키(허용 목록 밖) {sorted(blank_en - INTENTIONALLY_BLANK_EN)}"


def test_placeholders_match_between_languages():
    """한국어와 영어의 %s·%d·{이름} 자리표시자가 같다(다르면 포맷 오류 또는 값이 사라진다)."""
    bad = [(row[0], PLACEHOLDER.findall(row[1]), PLACEHOLDER.findall(row[2])) for row in rows()[1:]
           if row[2].strip() and sorted(PLACEHOLDER.findall(row[1])) != sorted(PLACEHOLDER.findall(row[2]))]
    assert not bad, f"{len(bad)}건 — {bad[:3]}"


def test_keys_used_in_code_exist():
    """코드가 글자 그대로 쓰는 키(Locale.t/tf/t_or/has 인자)가 모두 CSV에 있다. 문자열을 이어 붙이는 키(끝이 _)는 뒤 테스트가 본다."""
    keys = {row[0] for row in rows()[1:]}
    missing = sorted((fn, k, sorted(fs)) for (fn, k), fs in used_keys().items() if not k.endswith("_") and k not in keys)
    assert not missing, f"{len(missing)}건 — {missing[:5]}"


def test_dynamic_key_families_have_entries_and_generic_fallback():
    """err_*_ 처럼 뒤를 동적으로 붙이는 키 묶음은 최소 하나는 있고, 표에 없는 코드를 대신할 일반 문구 err_generic이 있다(2026-11-05)."""
    keys = {row[0] for row in rows()[1:]}
    prefixes = sorted(k for (fn, k) in used_keys() if k.endswith("_"))
    assert prefixes, "동적 키 접두어를 찾지 못함"
    empty = [p for p in prefixes if not any(k.startswith(p) for k in keys)]
    assert not empty, f"항목이 하나도 없는 접두어 {empty}"
    assert "err_generic" in keys, "err_generic 없음"


def test_tf_keys_have_placeholders():
    """Locale.tf(key, args)로 쓰는 키는 한국어·영어 모두 자리표시자가 있다(없으면 % 포맷이 오류)."""
    by_key = {row[0]: row for row in rows()[1:]}
    bad = [k for (fn, k) in used_keys() if fn == "tf" and k in by_key
           and not (PLACEHOLDER.search(by_key[k][1]) and (PLACEHOLDER.search(by_key[k][2]) or not by_key[k][2].strip()))]
    assert not bad, f"{bad}"


def test_mark_labels_exist_for_all_marks():
    """마크 8종(DESIGN §5)마다 mark_<이름> 문구가 있다."""
    keys = {row[0] for row in rows()[1:]}
    missing = [f"mark_{m}" for m in MARKS if f"mark_{m}" not in keys]
    assert not missing, f"{missing}"
