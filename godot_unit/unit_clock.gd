extends RefCounted
# 모듈 21 — 곡 시계와 보정 (MusicPlayer 클록: start_clock·start_silent·pause·resume·stop, TimingManager: 보정 저장·범위·지연 합 — 기준 DESIGN §10 스크롤/타이밍)
#   - 곡 시계는 시스템 시계 기준: 시작 위치에서 시간이 지날수록 커진다, 카운트다운용 음수 시작(-3000ms) 지원
#   - 일시정지하면 위치가 고정되고, 재개하면 그 위치에서 이어 간다(리셋 안 됨), 정지하면 0
#   - 보정: ±200ms 로 자르고(CALIBRATION_RANGE_MS) user://calibration.cfg 에 저장, 다시 읽으면 같은 값, 총 지연 = 시스템 지연 + 보정
# 서버는 쓰지 않는다. 시계 시험은 실제 시간이 흐르므로 허용 오차(300ms)를 둔다 — 이 값과 기다리는 시간(40ms)은 시험 작성자가 정했다.

const SLACK := 300.0

var needs_frames := true
var results: Array = []
var _saved_cal := 0.0
var _saved_sys := 0.0


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	TimingManager.system_latency_ms = _saved_sys
	TimingManager.set_user_calibration(_saved_cal)


func run() -> Array:
	_saved_cal = TimingManager.user_calibration_ms
	_saved_sys = TimingManager.system_latency_ms

	# ── 곡 시계 ──
	var mp := MusicPlayer.new()
	eq("시작 전: 위치 0, 재생 중 아님", [mp.get_position_ms(), mp.is_playing_music], [0.0, false])
	mp.start_clock(-3000.0)
	check("음수 시작(-3000ms 카운트다운): 재생 중 표시", mp.is_playing_music)
	var p0 := mp.get_position_ms()
	check("음수 시작 직후 위치가 -3000 근처", p0 >= -3000.0 and p0 <= -3000.0 + SLACK, "p0=%s" % p0)
	OS.delay_msec(40)
	var p1 := mp.get_position_ms()
	check("시간이 지나면 위치가 커짐(40ms 뒤)", p1 > p0 and p1 - p0 <= SLACK, "%s → %s" % [p0, p1])
	mp.pause_music()
	var paused := mp.get_position_ms()
	OS.delay_msec(40)
	eq("일시정지: 시간이 지나도 위치 고정", mp.get_position_ms(), paused)
	check("일시정지 위치는 직전 위치 이후", paused >= p1 and paused - p1 <= SLACK, "paused=%s p1=%s" % [paused, p1])
	mp.resume_music()
	var r0 := mp.get_position_ms()
	check("재개: 일시정지 위치에서 이어 감(리셋되지 않음)", r0 >= paused and r0 - paused <= SLACK, "paused=%s resumed=%s" % [paused, r0])
	OS.delay_msec(40)
	check("재개 뒤 시간이 다시 흐름", mp.get_position_ms() > r0)
	mp.stop_music()
	eq("정지: 재생 중 아님, 위치 0", [mp.is_playing_music, mp.get_position_ms()], [false, 0.0])
	mp.start_silent()
	var s0 := mp.get_position_ms()
	check("음악 없이 시계만 시작: 0 근처에서 시작", s0 >= 0.0 and s0 <= SLACK, "s0=%s" % s0)
	mp.stop_music()
	mp.free()

	# ── 보정 ──
	eq("보정 범위 상수 ±200", TimingManager.CALIBRATION_RANGE_MS, 200.0)
	TimingManager.set_user_calibration(55.0)
	eq("보정 55: 그대로 저장", TimingManager.user_calibration_ms, 55.0)
	TimingManager.set_user_calibration(500.0)
	eq("보정 500: +200 으로 자름", TimingManager.user_calibration_ms, 200.0)
	TimingManager.set_user_calibration(-500.0)
	eq("보정 -500: -200 으로 자름", TimingManager.user_calibration_ms, -200.0)
	TimingManager.set_user_calibration(-37.5)
	TimingManager.user_calibration_ms = 0.0
	TimingManager._load_calibration()
	eq("저장한 보정을 다시 읽으면 같은 값(-37.5)", TimingManager.user_calibration_ms, -37.5)
	var cfg := ConfigFile.new()
	eq("calibration.cfg 에 audio/user_calibration_ms 로 저장됨", [cfg.load("user://calibration.cfg"), cfg.get_value("audio", "user_calibration_ms", null)], [OK, -37.5])

	# ── 지연 합 ──
	TimingManager.system_latency_ms = 12.0
	TimingManager.set_user_calibration(30.0)
	eq("총 지연 = 시스템 지연 + 보정", TimingManager.get_total_latency_ms(), 42.0)
	var t_a := TimingManager.get_precise_time()
	OS.delay_msec(20)
	var t_b := TimingManager.get_precise_time()
	check("정밀 시간(초)이 흐름", t_b > t_a and t_b - t_a < 1.0, "%s → %s" % [t_a, t_b])
	var corrected := TimingManager.get_corrected_time() - TimingManager.get_precise_time()
	check("보정된 시간 = 정밀 시간 + 총 지연(0.042초)", absf(corrected - 0.042) < 0.01, "차이 %s" % corrected)
	return results
