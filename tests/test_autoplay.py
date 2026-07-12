# -*- coding: utf-8 -*-
"""오토플레이 결과 검증 테스트 — 1판만 플레이하고 전체 검증"""
import pytest
from conftest import play_one_round

VALID_GRADES = {"MAX", "S++", "S+", "S", "A", "B", "C", "D", "F"}
VALID_CLEAR  = {"Expert", "Hard", "Normal", "Easy", "GameOver"}


@pytest.fixture(scope="module")
def res():
    return play_one_round()


def test_score_positive(res):
    assert res["score"] > 0


def test_accuracy_range(res):
    assert 0.0 <= res["accuracy"] <= 100.0


def test_grade_valid(res):
    assert res["grade"] in VALID_GRADES


def test_clear_grade_valid(res):
    assert res["clear_grade"] in VALID_CLEAR


def test_autoplay_not_failed(res):
    assert res["clear_grade"] != "GameOver"


def test_judgment_sum_positive(res):
    total = res["wow"] + res["great"] + res["good"] + res["oops"] + res["miss"]
    assert total > 0


def test_max_combo_positive(res):
    assert res["max_combo"] > 0
