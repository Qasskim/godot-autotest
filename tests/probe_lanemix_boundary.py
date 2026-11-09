import sys, time, random, json, glob, os
sys.path.insert(0, r"D:\Automation\RhythmGame_AutoTest\tests")
import godot_runner, client
from screen_helpers import press, wait_until
seed = int(sys.argv[1]); delta = float(sys.argv[2]); win_before = float(sys.argv[3]); win_after = float(sys.argv[4])
proc = godot_runner.start_game()
try:
    client.navigate("song_select"); client.wait_for_scene("SongSelect", timeout=15)
    wait_until(lambda: client.songs()["count"] > 0, timeout=10); time.sleep(1.2)
    titles = client.songs()["songs"]
    title = random.Random(seed).choice([t for t in titles if t.startswith("TECHNO")])
    client.tap_song_at(titles.index(title)); time.sleep(0.5)
    client.autoplay(True); client.autolanemix(False)
    press("PLAY"); client.wait_for_scene("GameScene", timeout=30)
    deadline = time.time() + 160
    while time.time() < deadline and client.lanemix_prompt()["state"] != "OFFER": time.sleep(0.05)
    p = client.lanemix_prompt(); start = p["section_starts"][0]
    chart = None
    for f in glob.glob(r"D:\Godot\RhythmGame_New\Godot\charts\keysound\techno_*\*EZ*.rgds"):
        d = json.load(open(f, encoding="utf-8"))
        st = [e["timing_ms"] for e in d.get("gimmick_events", []) if e.get("action") == "lanemix_start"]
        if st and abs(st[0] - start) < 1: chart = d
    notes = [n for n in chart["score"] if n.get("type") == "tap" and n["lane"] < 32 and start - win_before <= n["timing_ms"] <= start + win_after]
    plan = ",".join(f"{n['timing_ms'] + delta:.2f}:{n['lane'] % 16}" for n in sorted(notes, key=lambda n: n["timing_ms"]))
    client._req("POST", "/debug_autoplay_live?on=0")
    client._req("POST", "/debug_press_plan?plan=" + plan)
    client.click(p["button_x"], p["button_y"])
    time.sleep((start + win_after - p["music_ms"]) / 1000 + 2)
    log = client._req("GET", "/debug_judgment_log")
    print(title, "start", start, "presses", len(log["presses"]), flush=True)
    allnotes = [n for n in chart["score"] if n["lane"] < 32 and start - win_before <= n["timing_ms"] <= start + win_after]
    print("chart notes (rel, type, lane, len):")
    for n in sorted(allnotes, key=lambda n: n["timing_ms"]):
        print(f"  {n['timing_ms']-start:7.1f} {n.get('type'):6s} lane={n['lane']:2d}", n.get("length_ms", ""), flush=True)
    print("presses:", [(round(x["ms"]-start,1), x["lane"], x["key_mode"], round(x["music_ms"]-start,1)) for x in log["presses"]])
    print("judgments (rel_music, lane, grade, err):")
    for j in log["judgments"]:
        print(f"  {j['music_ms']-start:7.1f} lane={j['lane']:2d} {j['grade']:6s} {j['error_ms']}", flush=True)
finally:
    godot_runner.stop_game(proc)
