# -*- coding: utf-8 -*-
"""마크 시스템 검증 — 1판만 플레이하고 전체 검증"""
import pytest
from conftest import play_one_round

VALID_MARKS = {"perfect", "allcombo", "allgood", "clear", "failed",
               "evil", "luckyroulette", "straight"}
EXCLUSIVE   = {"perfect", "allcombo", "allgood"}


@pytest.fixture(scope="module")
def res():
    return play_one_round()


def test_marks_all_valid(res):
    for m in res.get("marks", []):
        assert m in VALID_MARKS, f"알 수 없는 마크: {m}"


def test_marks_has_clear_or_failed(res):
    marks = res.get("marks", [])
    assert "clear" in marks or "failed" in marks


def test_clear_and_failed_not_both(res):
    marks = res.get("marks", [])
    assert not ("clear" in marks and "failed" in marks)


def test_exclusive_marks_at_most_one(res):
    marks = res.get("marks", [])
    found = [m for m in marks if m in EXCLUSIVE]
    assert len(found) <= 1, f"exclusive 마크 중복: {found}"


def test_autoplay_gets_perfect(res):
    marks = res.get("marks", [])
    assert "perfect" in marks, \
        f"오토플레이인데 perfect 없음: {marks} (miss={res['miss']}, oops={res['oops']}, good={res['good']})"
