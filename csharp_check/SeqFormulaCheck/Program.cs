using System;
using System.Globalization;
using RGDSSequencer.Models;
using RGDSSequencer.Services;

// 시퀀서의 음량(NoteData.Gain)·pan(PanLaw.Gains)·값 자르기(Set*) 결과를 한 줄씩 JSON 비슷한 텍스트로 출력한다.
// 파이썬 시험이 이 출력을 읽어 게임(GDScript) 결과 및 문서의 공식과 비교한다.
var inv = CultureInfo.InvariantCulture;
for (int pan = -127; pan <= 127; pan++)
{
    PanLaw.Gains(pan, out float l, out float r);
    Console.WriteLine($"PAN {pan} {l.ToString("R", inv)} {r.ToString("R", inv)}");
}
foreach (int v in new[] { 1, 2, 32, 63, 64, 65, 100, 127 })
    foreach (float vol in new[] { 0f, 50f, 100f, 150f, 200f })
    {
        var n = new NoteData();
        n.SetVelocity(v);
        n.SetVolume(vol);
        Console.WriteLine($"GAIN {v} {vol.ToString("R", inv)} {n.Gain.ToString("R", inv)}");
    }
foreach (int v in new[] { -5, 0, 500 })
{
    var n = new NoteData(); n.SetVelocity(v);
    Console.WriteLine($"CLAMPV {v} {n.VelocityValue}");
}
foreach (float vol in new[] { -10f, 300f })
{
    var n = new NoteData(); n.SetVolume(vol);
    Console.WriteLine($"CLAMPVOL {vol.ToString("R", inv)} {n.VolumeValue.ToString("R", inv)}");
}
foreach (int p in new[] { -200, 200 })
{
    var n = new NoteData(); n.SetPan(p);
    Console.WriteLine($"CLAMPPAN {p} {n.PanValue}");
}
var d = new NoteData();
d.SetVelocity(64); d.SetVolume(100f); d.SetPan(0);
Console.WriteLine($"DEFAULTS_NULL {(d.Velocity == null ? 1 : 0)} {(d.Volume == null ? 1 : 0)} {(d.Pan == null ? 1 : 0)}");
