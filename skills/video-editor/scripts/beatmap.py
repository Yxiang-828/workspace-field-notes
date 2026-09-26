# beatmap.py — scan a song (or a video's audio) for its rhythmic structure so an edit
#               can cut ON the beat. Emits a beatmap JSON that montage.py consumes.
#   py beatmap.py song.mp3 [out.beats.json]      # default: <song>.beats.json
#   py beatmap.py clip.mp4                        # extracts the audio track first
#
# Output JSON:
#   { source, duration, bpm, beat_period,
#     beats:[t...],        # every beat (rhythmic cut grid)
#     downbeats:[t...],    # bar starts (big section / hero cuts)        [4/4 assumed]
#     onsets:[t...],       # transients (snap "hit" effects to these)
#     drops:[t...],        # energy surges = chorus/drop (stack the "hit" combo here)
#     beat_energy:[0..1],  # normalized loudness at each beat (drives section pacing)
#     sections:[{start,end,level}] }   # low|mid|high energy spans
#
# librosa is the engine (pip install librosa soundfile). If it can't import, falls back
# to an ffmpeg astats energy timeline (onsets+drops+a guessed grid, no true BPM).
import json, os, subprocess, sys

FFMPEG = r"C:\ffmpeg\bin\ffmpeg" if os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe") else "ffmpeg"
FFPROBE = r"C:\ffmpeg\bin\ffprobe" if os.path.exists(r"C:\ffmpeg\bin\ffprobe.exe") else "ffprobe"
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus")


def dur_of(f):
    return float(subprocess.check_output(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).strip())


def extract_audio(video, wav):
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", video, "-vn", "-ac", "1",
                    "-ar", "22050", wav], check=True)
    return wav


def collapse(times, gap):
    out = []
    for t in sorted(times):
        if not out or t - out[-1] > gap:
            out.append(float(t))
    return out


def analyze_librosa(path):
    import librosa, numpy as np
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    bpm = float(np.atleast_1d(tempo)[0])
    beats = librosa.frames_to_time(beat_frames, sr=sr)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, backtrack=True)
    onsets = librosa.frames_to_time(onset_frames, sr=sr)

    # per-beat loudness (RMS at each beat) -> normalized 0..1 energy curve
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    if len(beats):
        be = np.interp(beats, t_rms, rms)
        lo, hi = np.percentile(be, 5), np.percentile(be, 95)
        beat_energy = np.clip((be - lo) / (hi - lo + 1e-9), 0, 1)
    else:
        beat_energy = np.array([])

    # downbeats: assume 4/4; pick the phase whose beats carry the most onset strength
    if len(beats) >= 4:
        ostr_at = np.interp(beats, t_rms, np.interp(t_rms,
                  librosa.frames_to_time(np.arange(len(onset_env)), sr=sr), onset_env))
        phase = max(range(4), key=lambda p: ostr_at[p::4].sum())
        downbeats = beats[phase::4]
    else:
        downbeats = beats[::4]

    # drops: large positive steps in ~1s-smoothed energy (2-sigma surges)
    win = max(1, int(1.0 * sr / hop))
    smooth = np.convolve(rms, np.ones(win) / win, mode="same")
    deriv = np.diff(smooth, prepend=smooth[0])
    thr = deriv.mean() + 2 * deriv.std()
    drops = collapse(t_rms[np.where(deriv > thr)[0]], gap=4.0)

    # sections: classify each beat interval lo/mid/high, merge runs
    sections = []
    if len(beats):
        lvls = ["low", "mid", "high"]
        labels = [lvls[min(2, int(e * 3))] for e in beat_energy]
        s = 0
        for i in range(1, len(labels) + 1):
            if i == len(labels) or labels[i] != labels[s]:
                start = float(beats[s]); end = float(beats[i]) if i < len(beats) else dur
                if end - start >= 1.5:  # ignore micro-spans
                    sections.append({"start": round(start, 3), "end": round(end, 3), "level": labels[s]})
                s = i

    return {
        "source": os.path.abspath(path), "duration": round(dur, 3),
        "bpm": round(bpm, 2), "beat_period": round(60.0 / bpm, 4) if bpm else None,
        "beats": [round(float(t), 3) for t in beats],
        "downbeats": [round(float(t), 3) for t in downbeats],
        "onsets": [round(float(t), 3) for t in onsets],
        "drops": [round(t, 3) for t in drops],
        "beat_energy": [round(float(e), 3) for e in beat_energy],
        "sections": sections, "engine": "librosa",
    }


def analyze_ffmpeg(path):
    """No-deps fallback: energy timeline via astats -> onsets+drops+guessed grid."""
    import re, statistics
    wav = path
    proc = subprocess.run(
        [FFMPEG, "-i", path, "-af",
         "asetnsamples=n=2205,astats=metadata=1:reset=1,"
         "ametadata=print:key=lavfi.astats.Overall.RMS_level",
         "-f", "null", "-"],
        stderr=subprocess.PIPE, text=True).stderr
    ts, db = [], []
    cur = None
    for line in proc.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m: cur = float(m.group(1))
        m = re.search(r"RMS_level=(-?[0-9.]+|-inf)", line)
        if m and cur is not None:
            ts.append(cur); db.append(-90.0 if m.group(1) == "-inf" else float(m.group(1)))
    if not ts:
        raise RuntimeError("ffmpeg astats produced no samples")
    lin = [10 ** (d / 20) for d in db]
    dur = dur_of(path)
    # onsets = positive jumps; drops = big jumps
    jumps = [lin[i] - lin[i - 1] for i in range(1, len(lin))]
    mu, sd = statistics.mean(jumps), (statistics.pstdev(jumps) or 1e-9)
    onsets = collapse([ts[i + 1] for i, j in enumerate(jumps) if j > mu + sd], 0.18)
    drops = collapse([ts[i + 1] for i, j in enumerate(jumps) if j > mu + 2.5 * sd], 4.0)
    # crude tempo from median onset spacing -> grid
    if len(onsets) > 4:
        diffs = sorted(onsets[i + 1] - onsets[i] for i in range(len(onsets) - 1))
        period = diffs[len(diffs) // 2] or 0.5
    else:
        period = 0.5
    period = min(max(period, 0.30), 1.2)
    beats = []
    t = onsets[0] if onsets else 0.0
    while t < dur:
        beats.append(round(t, 3)); t += period
    return {
        "source": os.path.abspath(path), "duration": round(dur, 3),
        "bpm": round(60.0 / period, 2), "beat_period": round(period, 4),
        "beats": beats, "downbeats": beats[::4], "onsets": onsets, "drops": drops,
        "beat_energy": [], "sections": [], "engine": "ffmpeg-fallback",
    }


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: py beatmap.py <song.mp3|clip.mp4> [out.beats.json]")
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".beats.json"

    tmp_wav = None
    apath = src
    if not src.lower().endswith(AUDIO_EXT):
        tmp_wav = out + ".tmp.wav"; apath = extract_audio(src, tmp_wav)

    try:
        bm = analyze_librosa(apath)
    except Exception as e:
        print(f"librosa unavailable/failed ({e}); using ffmpeg fallback", file=sys.stderr)
        bm = analyze_ffmpeg(apath)
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            os.remove(tmp_wav)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(bm, f, indent=1)
    print(f"beatmap -> {out}")
    print(f"  engine={bm['engine']}  bpm={bm['bpm']}  dur={bm['duration']}s  "
          f"{len(bm['beats'])} beats / {len(bm['downbeats'])} downbeats / "
          f"{len(bm['onsets'])} onsets / {len(bm['drops'])} drops / {len(bm['sections'])} sections")


if __name__ == "__main__":
    main()
