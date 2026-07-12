# -*- coding: utf-8 -*-
"""씬 전환 플로우 테스트"""
import client


def test_ping():
    assert client.ping()


def test_navigate_to_main_menu():
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)


def test_navigate_to_song_select():
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)


def test_full_flow():
    """MainMenu → SongSelect → GameScene(autoplay) → ResultScreen → SongSelect"""
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)

    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    client.autoplay(True)

    client.tap("first_song")
    client.tap("play")
    assert client.wait_for_scene("GameScene", timeout=15)

    client.wait_game_finished()
    assert client.wait_for_scene("ResultScreen", timeout=15)
    assert "score" in client.result()

    client.tap("select_song")
    assert client.wait_for_scene("SongSelect", timeout=15)

    client.autoplay(False)
