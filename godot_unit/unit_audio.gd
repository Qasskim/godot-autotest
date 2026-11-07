extends RefCounted
# 모듈 12(게임 쪽) — 키음 음량·pan 공식 (기준: Godot/docs/DESIGN.md §8 "노트별 velocity / volume / pan")
#   음량 = velocity/64 × volume/100 (velocity 1~127, volume 0~200), pan 은 밸런스 방식 — 치우친 반대쪽 채널만 cos(|pan|/127×90°)로 줄임.
# 시퀀서(C#)와 같은 공식이어야 하므로(PanLaw.cs 주석), 이 모듈이 게임 결과를 수치표로 내보내고 test_cross_formula.py 가 C# 결과와 비교한다.

const ChartLoader := preload("res://scripts/chart/ChartLoader.gd")
const AMP := 20000          # 합성 키음의 샘플 크기(양쪽 채널 같은 값)

var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func near(name: String, actual: float, expected: float, tol: float = 1e-6) -> void:
	check(name, absf(actual - expected) <= tol, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	pass


func _wav() -> AudioStreamWAV:
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.stereo = true
	w.mix_rate = 44100
	var d := PackedByteArray()
	d.resize(8 * 4)                       # 8프레임 × (왼쪽 2바이트 + 오른쪽 2바이트)
	for i in 8:
		d.encode_s16(i * 4, AMP)
		d.encode_s16(i * 4 + 2, AMP)
	w.data = d
	return w


func run() -> Array:
	# ── 음량 (velocity × volume) ──
	near("음량: 값이 없으면 기준(velocity 64, volume 100) = 1.0", ChartLoader.note_gain({}), 1.0)
	near("음량: velocity 127 = 127/64 (약 2배)", ChartLoader.note_gain({"velocity": 127}), 127.0 / 64.0)
	near("음량: velocity 1 = 1/64", ChartLoader.note_gain({"velocity": 1}), 1.0 / 64.0)
	near("음량: volume 200 = 2.0 배", ChartLoader.note_gain({"volume": 200}), 2.0)
	near("음량: volume 0 = 무음", ChartLoader.note_gain({"volume": 0}), 0.0)
	near("음량: 최종 음량 = velocity/64 × volume/100 (100, 150)", ChartLoader.note_gain({"velocity": 100, "volume": 150}), 100.0 / 64.0 * 1.5)
	near("음량: 범위 밖 velocity(500)는 127로 자름", ChartLoader.note_gain({"velocity": 500}), 127.0 / 64.0)
	near("음량: 범위 밖 velocity(-5)는 1로 자름", ChartLoader.note_gain({"velocity": -5}), 1.0 / 64.0)
	near("음량: 범위 밖 volume(300)은 200으로, (-10)은 0으로 자름", ChartLoader.note_gain({"volume": 300}) + ChartLoader.note_gain({"volume": -10}), 2.0)
	# ── pan 값 ──
	eq("pan 값: 없으면 기준 0(가운데)", ChartLoader.note_pan({}), 0)
	eq("pan 값: -127~127로 자름", [ChartLoader.note_pan({"pan": -200}), ChartLoader.note_pan({"pan": 200}), ChartLoader.note_pan({"pan": 50})], [-127, 127, 50])
	# ── pan 적용(밸런스 방식) ──
	var center: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), 0)
	eq("pan 적용: 가운데(0)는 양쪽 채널을 그대로 둠", [center.data.decode_s16(0), center.data.decode_s16(2)], [AMP, AMP])
	var right: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), 127)
	eq("pan 적용: 오른쪽 끝(127)은 왼쪽을 거의 0으로(cos 90° ≈ 6e-17 → 0), 오른쪽은 그대로", [right.data.decode_s16(0), right.data.decode_s16(2)], [0, AMP])
	var left: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), -127)
	eq("pan 적용: 왼쪽 끝(-127)은 오른쪽을 0으로, 왼쪽은 그대로", [left.data.decode_s16(0), left.data.decode_s16(2)], [AMP, 0])
	var half: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), 64)
	var want_far := int(AMP * cos(64.0 / 127.0 * PI / 2.0))
	eq("pan 적용: 오른쪽 64는 왼쪽만 cos(64/127×90°) 배(트렁케이트)로 줄고 오른쪽은 그대로", [half.data.decode_s16(0), half.data.decode_s16(2)], [want_far, AMP])
	eq("pan 적용: 형식 유지(16비트 스테레오, 샘플레이트, 프레임 수)", [half.format, half.stereo, half.mix_rate, half.data.size()], [AudioStreamWAV.FORMAT_16_BITS, true, 44100, 32])
	var mono_pos := true
	var prev := AMP + 1
	for p in range(0, 128):
		var o: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), p)
		var far := o.data.decode_s16(0)
		if far > prev or o.data.decode_s16(2) != AMP:
			mono_pos = false
		prev = far
	check("pan 적용: 오른쪽으로 갈수록 왼쪽 채널은 줄기만 하고(0~127) 오른쪽 채널은 늘 그대로", mono_pos)
	var sym := true
	for p in range(1, 128):
		var a: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), p)
		var b: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), -p)
		if a.data.decode_s16(0) != b.data.decode_s16(2):
			sym = false
	check("pan 적용: 좌우 대칭(pan p 의 왼쪽 결과 = pan -p 의 오른쪽 결과, 1~127)", sym)

	# ── 교차 비교용 수치표 ──
	var pan_rows: Array = []
	for p in range(-127, 128):
		var o2: AudioStreamWAV = KeySoundManager._apply_pan(_wav(), p)
		pan_rows.append([p, o2.data.decode_s16(0), o2.data.decode_s16(2)])
	var gain_rows: Array = []
	for v in [1, 2, 32, 63, 64, 65, 100, 127]:
		for vol in [0, 50, 100, 150, 200]:
			gain_rows.append([v, vol, ChartLoader.note_gain({"velocity": v, "volume": vol})])
	var clamp_rows := {
		"vel_-5": ChartLoader.note_gain({"velocity": -5}), "vel_0": ChartLoader.note_gain({"velocity": 0}), "vel_500": ChartLoader.note_gain({"velocity": 500}),
		"vol_-10": ChartLoader.note_gain({"volume": -10}), "vol_300": ChartLoader.note_gain({"volume": 300}),
		"pan_-200": ChartLoader.note_pan({"pan": -200}), "pan_200": ChartLoader.note_pan({"pan": 200}),
	}
	results.append({"name": "교차 비교용 수치표: 게임의 pan 적용 결과 255개·음량 40개·자르기 값 (test_cross_formula.py 가 C#과 비교)", "pass": true,
		"detail": JSON.stringify({"amp": AMP, "pan": pan_rows, "gain": gain_rows, "clamp": clamp_rows})})
	return results
