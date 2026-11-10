extends RefCounted
# 모듈 18 — 오디오 버스 적용 (AudioManager: 버스 4개, 음량 슬라이더→dB, 음소거, 키음 음량, 곡 소리 이퀄라이저 — 기준 DESIGN §12 오디오 버스 구조·볼륨/음소거·이퀄라이저)
#   - 버스: BGM · KeySound · SFX · EventSfx 가 있고 Master 로 보낸다
#   - 음량: 슬라이더 선형값 → dB (1.0 = 0dB, 0.5 = −6.02dB, 0 은 −80dB 로 바닥), 없는 버스 이름은 오류 없이 무시
#   - 음소거: 켜고 끄기, 음량과 독립
#   - 이퀄라이저: 전부 0 이면 이펙트를 붙이지 않고, 올리면 (앰프 → EQ) 가 붙어 올린 최대 밴드만큼 앰프가 낮춘다(자동 프리앰프, DESIGN §12), 다시 0 이면 꺼진다, 내리기만 하면 앰프는 0
#   - 키음 재생 음량: 재생기 음량 = linear_to_db(gain), gain 0 이하·빈 스트림은 재생하지 않음
# 소리가 실제로 들리는지는 사람이 확인한다. 기대값은 DESIGN 문장과 손계산이다. 서버는 쓰지 않는다.

const TOL := 0.01

var needs_frames := true
var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func near(name: String, actual: float, expected: float) -> void:
	check(name, absf(actual - expected) <= TOL, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	AudioManager.set_bus_muted("BGM", false)
	AudioManager.set_bus_volume_linear("BGM", 1.0)


func bus_db(name: String) -> float:
	return AudioServer.get_bus_volume_db(AudioServer.get_bus_index(name))


func effect_state() -> Dictionary:
	var idx := AudioServer.get_bus_index("KeySound")
	var out := {"count": AudioServer.get_bus_effect_count(idx), "amp": null, "eq": null, "amp_on": false, "eq_on": false}
	for i in out.count:
		var e := AudioServer.get_bus_effect(idx, i)
		if e is AudioEffectAmplify:
			out.amp = e
			out.amp_on = AudioServer.is_bus_effect_enabled(idx, i)
		elif e is AudioEffectEQ10:
			out.eq = e
			out.eq_on = AudioServer.is_bus_effect_enabled(idx, i)
	return out


func make_stream() -> AudioStreamWAV:
	var s := AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = 22050
	var data := PackedByteArray()
	data.resize(4000)
	s.data = data
	return s


func run() -> Array:
	# ── 버스 ──
	for b in ["BGM", "KeySound", "SFX", "EventSfx"]:
		var i := AudioServer.get_bus_index(b)
		check("버스 %s 가 있음" % b, i != -1)
		if i != -1:
			eq("버스 %s 는 Master 로 보냄" % b, str(AudioServer.get_bus_send(i)), "Master")

	# ── 음량(선형 → dB) ──
	AudioManager.set_bus_volume_linear("BGM", 1.0)
	near("선형 1.0 → 0dB", bus_db("BGM"), 0.0)
	AudioManager.set_bus_volume_linear("BGM", 0.5)
	near("선형 0.5 → −6.02dB", bus_db("BGM"), -6.0206)
	AudioManager.set_bus_volume_linear("BGM", 0.1)
	near("선형 0.1 → −20dB", bus_db("BGM"), -20.0)
	AudioManager.set_bus_volume_linear("BGM", 0.0)
	near("선형 0 → 바닥(−80dB)", bus_db("BGM"), -80.0)
	AudioManager.set_bus_volume_linear("BGM", -1.0)
	near("선형 음수도 바닥으로 자름", bus_db("BGM"), -80.0)
	AudioManager.set_bus_volume("BGM", -12.5)
	near("dB 직접 지정", bus_db("BGM"), -12.5)
	AudioManager.set_bus_volume_linear("없는버스", 0.5)
	AudioManager.set_bus_muted("없는버스", true)
	AudioManager.set_bus_volume("없는버스", -3.0)
	check("없는 버스 이름: 오류 없이 무시", true)

	# ── 음소거 ──
	var bgm := AudioServer.get_bus_index("BGM")
	AudioManager.set_bus_volume_linear("BGM", 0.5)
	AudioManager.set_bus_muted("BGM", true)
	eq("음소거 켜기", AudioServer.is_bus_mute(bgm), true)
	near("음소거 중에도 음량 값은 그대로", bus_db("BGM"), -6.0206)
	AudioManager.set_bus_muted("BGM", false)
	eq("음소거 끄기", AudioServer.is_bus_mute(bgm), false)

	# ── 이퀄라이저 ──
	var flat := [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
	var before := effect_state()
	AudioManager.apply_keysound_eq(flat)
	eq("전부 0: 이펙트를 새로 붙이지 않음", effect_state().count, before.count)
	var boost := [6.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -2.0]
	AudioManager.apply_keysound_eq(boost)
	var st := effect_state()
	check("올리면 앰프와 EQ 가 붙음", st.amp != null and st.eq != null and st.count == before.count + 2, str(st.count))
	if st.amp != null and st.eq != null:
		near("자동 프리앰프: 올린 최대 6dB 만큼 앰프가 낮춤(−6dB)", st.amp.volume_db, -6.0)
		eq("EQ 밴드 수 10", st.eq.get_band_count(), 10)
		var got := []
		for b in 10:
			got.append(st.eq.get_band_gain_db(b))
		eq("EQ 밴드 값이 그대로 들어감", got, boost)
		eq("올리면 이펙트가 켜져 있음", [st.amp_on, st.eq_on], [true, true])
		AudioManager.apply_keysound_eq(flat)
		st = effect_state()
		eq("다시 전부 0: 이펙트를 꺼서 처리 비용을 없앰(붙은 채로 비활성)", [st.amp_on, st.eq_on, st.count], [false, false, before.count + 2])
		AudioManager.apply_keysound_eq([-3.0, -3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
		st = effect_state()
		near("내리기만 하면 앰프는 보정하지 않음(0dB)", st.amp.volume_db, 0.0)
		eq("내리기만 해도 이퀄라이저는 켜짐", [st.amp_on, st.eq_on], [true, true])
		eq("짧은 목록(밴드 2개)도 오류 없이 앞 밴드만 적용", [st.eq.get_band_gain_db(0), st.eq.get_band_gain_db(1)], [-3.0, -3.0])
		AudioManager.apply_keysound_eq(flat)

	# ── 키음 재생 음량 ──
	var stream := make_stream()
	var players: Array = AudioManager._ks_players
	AudioManager.play_keysound(stream, 0.5)
	var used = null
	for p in players:
		if p.stream == stream:
			used = p
	check("키음을 재생하면 재생기 하나가 그 스트림을 받음", used != null)
	if used != null:
		near("키음 재생 음량 = linear_to_db(0.5) (−6.02dB)", used.volume_db, -6.0206)
	AudioManager.stop_all()
	var stream_zero := make_stream()
	AudioManager.play_keysound(stream_zero, 0.0)
	AudioManager.play_keysound(null, 1.0)
	var taken := false
	for p in players:
		if p.stream == stream_zero:
			taken = true
	eq("gain 0 이하 키음은 재생기를 쓰지 않음", taken, false)
	AudioManager.stop_all()
	return results
