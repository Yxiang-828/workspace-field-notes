# montage.py — build a BEAT-SYNCED montage/edit: cut a pool of clips onto a song's beat
#   grid, pace by section energy, fire effects (zoom-punch / flash / shake / rgb / slow-mo
#   "hit" on drops), lay the music as the master track. ffmpeg + beatmap.py under the hood.
#     py montage.py montage.json        (run with Bash sandbox OFF)
#
# montage.json:
# {
#   "music": "song.mp3",            # master audio (required)
#   "beatmap": null,                # path to <song>.beats.json; auto-generated if absent
#   "output": {"w":1920,"h":1080,"fps":30,"file":"out.mp4"},
#   "clips": ["a.mp4", ...],        # clip pool (files); and/or:
#   "clips_dir": "C:/.../video",    # folder of clips (globbed)
#   "start": 0, "duration": 30,     # song window to edit over (s); duration null = whole song
#   "grid": "beat",                 # "beat" | "downbeat" | "half" (½-beat = hype)
#   "pace": true,                   # hold longer in low-energy sections, fast in high
#   "min_cut": 0.28,                # never cut faster than this (s)
#   "shuffle": true, "seed": 7,
#   "effects": { "zoom_punch":true, "flash":"drop", "hit":true, "shake":"drop",
#                "rgb":"drop", "slowmo":true, "grade":"cinematic",
#                "vignette":true, "grain":false },
#   "captions": [ {"at":"0:04","text":"DROP","dur":1.2} ]   # optional beat-timed overlays
# }
# "flash"/"shake"/"rgb": "all" | "drop" | "none".  Times are SONG time.
import json, os, sys, glob, math, random, subprocess

FFMPEG = r"C:\ffmpeg\bin\ffmpeg" if os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe") else "ffmpeg"
FFPROBE = r"C:\ffmpeg\bin\ffprobe" if os.path.exists(r"C:\ffmpeg\bin\ffprobe.exe") else "ffprobe"
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "C\\:/Windows/Fonts/arialbd.ttf"
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".m4v")

GRADES = {  # name -> extra video filter appended in the final pass
    "cinematic": "eq=contrast=1.07:saturation=1.10:brightness=0.01,curves=preset=medium_contrast",
    "warm":      "eq=saturation=1.12,colorbalance=rm=.05:gm=.02:bs=-.04",
    "cold":      "eq=saturation=1.05,colorbalance=rm=-.04:bs=.06",
    "vivid":     "eq=contrast=1.10:saturation=1.30",
    "noir":      "hue=s=0,eq=contrast=1.18",
    "vintage":   "curves=preset=vintage,eq=saturation=0.9",
}


def t2s(t):
    if isinstance(t, (int, float)): return float(t)
    s = 0.0
    for p in str(t).split(":"): s = s * 60 + float(p)
    return s

def dur_of(f):
    return float(subprocess.check_output(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).strip())

def run(cmd):
    r = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg step failed:\n  " + " ".join(map(str, cmd[:6])) + " …\n" + r.stderr[-800:])

def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    D = os.path.dirname(os.path.abspath(sys.argv[1]))
    P = lambda r: r if (r and os.path.isabs(r)) else os.path.join(D, r)

    o = spec.get("output", {}); W, H, FPS = o.get("w", 1920), o.get("h", 1080), o.get("fps", 30)
    outfile = P(o["file"])
    music = P(spec["music"])
    if not os.path.exists(music): sys.exit(f"music not found: {music}")

    # ---- clip pool ----
    clips = [P(c) for c in spec.get("clips", [])]
    if spec.get("clips_dir"):
        cd = P(spec["clips_dir"])
        clips += sorted(f for f in glob.glob(os.path.join(cd, "*")) if f.lower().endswith(VIDEO_EXT))
    clips = [c for c in clips if os.path.exists(c)]
    if not clips: sys.exit("no clips found (set 'clips' and/or 'clips_dir')")
    rnd = random.Random(spec.get("seed", 7))
    if spec.get("shuffle", True): rnd.shuffle(clips)
    cdur = {}
    for c in clips:
        try: cdur[c] = dur_of(c)
        except Exception: cdur[c] = 0.0
    clips = [c for c in clips if cdur[c] > 0.3]

    # ---- beatmap ----
    bmpath = P(spec["beatmap"]) if spec.get("beatmap") else os.path.splitext(music)[0] + ".beats.json"
    if not os.path.exists(bmpath):
        print(f"no beatmap; analyzing {os.path.basename(music)} ...")
        run([sys.executable, os.path.join(HERE, "beatmap.py"), music, bmpath])
    bm = json.load(open(bmpath, encoding="utf-8"))
    beats, downbeats = bm["beats"], bm["downbeats"]
    drops, sections = set(round(d, 2) for d in bm["drops"]), bm.get("sections", [])

    # ---- window ----
    start = t2s(spec.get("start", 0))
    song = bm["duration"]
    dur = spec.get("duration")
    dur = (song - start) if dur in (None, "full") else t2s(dur)
    end = min(start + dur, song)

    def level_at(t):
        for s in sections:
            if s["start"] <= t < s["end"]: return s["level"]
        return "mid"
    def near_drop(t):
        return any(abs(t - d) <= 0.18 for d in bm["drops"])

    # ---- build cut points from the grid + section pacing ----
    grid = spec.get("grid", "beat")
    base = downbeats if grid == "downbeat" else beats
    g = [t for t in base if start <= t < end]
    if not g:  # window has no beats (e.g. ambient intro) — snap to the first real beat
        later = [t for t in base if t >= start and t < end]
        nxt = [t for t in base if t >= start]
        if nxt and nxt[0] < song:
            start = nxt[0]; end = min(start + dur, song)
            g = [t for t in base if start <= t < end]
            print(f"  (no beats at window start; shifted start to first beat {start:.2f}s)")
    if grid == "half":  # insert midpoints between beats for hype density
        half = []
        for i in range(len(g) - 1):
            half += [g[i], (g[i] + g[i + 1]) / 2]
        g = half + ([g[-1]] if g else [])
    if not g: g = [start]
    pace = spec.get("pace", True)
    cuts, i = [], 0
    while i < len(g):
        cuts.append(g[i])
        step = 2 if (pace and level_at(g[i]) == "low") else 1
        i += step
    cuts.append(end)
    # enforce min_cut by merging too-close points
    min_cut = float(spec.get("min_cut", 0.28))
    merged = [cuts[0]]
    for t in cuts[1:]:
        if t - merged[-1] >= min_cut: merged.append(t)
    if merged[-1] < end - 0.05: merged[-1] = end
    cuts = merged
    segs = list(zip(cuts[:-1], cuts[1:]))
    if not segs: sys.exit("no segments — check start/duration vs song length")

    fx = spec.get("effects", {})
    def on(key, is_drop):
        v = fx.get(key, "none")
        return v is True or v == "all" or (v == "drop" and is_drop)

    print(f"montage: {len(segs)} cuts over {start:.1f}-{end:.1f}s  bpm={bm['bpm']}  "
          f"grid={grid} pace={pace}  clips={len(clips)}  drops_in_window="
          f"{sum(1 for d in bm['drops'] if start<=d<end)}")

    tmp = outfile + ".segs"; os.makedirs(tmp, exist_ok=True)
    seg_files = []
    ZN = max(2, int(0.22 * FPS))  # zoom-punch ease length (frames)

    for idx, (a, b) in enumerate(segs):
        slot = round(b - a, 3)
        is_drop = near_drop(a) or (round(a, 2) in drops)
        clip = clips[idx % len(clips)]
        slowmo = is_drop and fx.get("slowmo", True) and on("hit", is_drop)
        slow = 1.5 if slowmo else 1.0
        need = slot / slow                       # source seconds to grab
        cd = cdur[clip]
        loop = cd < need + 0.1
        inpt = 0.0 if loop else rnd.uniform(0, max(0.0, cd - need - 0.05))

        chain = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                 f"fps={FPS},trim=0:{need:.3f},setpts=PTS-STARTPTS")
        if slow != 1.0:
            chain += f",setpts={slow}*PTS"
        # shake (whole short drop segment)
        if on("shake", is_drop):
            A = 12
            chain += (f",crop=iw-{2*A}:ih-{2*A}:"
                      f"x='{A}+{A}*sin(2*PI*t*11)':y='{A}+{A}*cos(2*PI*t*9)',scale={W}:{H}")
        # rgb / chromatic split
        if on("rgb", is_drop):
            chain += ",rgbashift=rh=5:bh=-5"
        # zoom punch (bigger on drops)
        if fx.get("zoom_punch", True) or is_drop:
            z0 = 1.30 if is_drop else 1.14
            chain += (f",zoompan=z='if(lte(on,{ZN}),{z0}-{z0-1:.3f}*on/{ZN},1)':"
                      f"x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':d=1:s={W}x{H}:fps={FPS}")
        # white flash in
        if on("flash", is_drop):
            chain += ",fade=t=in:st=0:d=0.07:color=white"
        chain += f",trim=0:{slot:.3f},setpts=PTS-STARTPTS,format=yuv420p"

        sf = os.path.join(tmp, f"s{idx:04d}.mp4"); seg_files.append(sf)
        cmd = [FFMPEG, "-y", "-v", "error"]
        if loop: cmd += ["-stream_loop", "-1"]
        cmd += ["-ss", f"{inpt:.3f}", "-i", clip, "-an", "-vf", chain,
                "-t", f"{slot:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-pix_fmt", "yuv420p", sf]
        run(cmd)
        if idx % 25 == 0 or idx == len(segs) - 1:
            print(f"  seg {idx+1}/{len(segs)}  {slot:.2f}s{'  DROP' if is_drop else ''}")

    # ---- concat segments (video only) ----
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("\n".join(f"file '{f.replace(os.sep,'/')}'" for f in seg_files))
    raw = outfile + ".raw.mp4"
    run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", raw])
    total = dur_of(raw)

    # ---- final pass: grade + vignette/grain + captions + music ----
    vf = []
    grade = fx.get("grade")
    if grade and grade in GRADES: vf.append(GRADES[grade])
    if fx.get("vignette", True): vf.append("vignette=PI/5")
    if fx.get("grain"): vf.append("noise=alls=8:allf=t")
    for cap in spec.get("captions", []):
        ct = t2s(cap["at"]) - start
        if ct < 0 or ct > total: continue
        cl = float(cap.get("dur", 1.2))
        vf.append(f"drawtext=fontfile='{FONT}':text='{esc(cap['text'])}':fontsize=84:"
                  f"fontcolor=white:borderw=5:bordercolor=black@0.7:x=(w-tw)/2:y=h*0.78:"
                  f"enable='between(t,{ct:.2f},{ct+cl:.2f})'")
    vchain = "[0:v]" + (",".join(vf) if vf else "null") + "[v]"
    afade = max(0.0, total - 1.5)
    achain = (f"[1:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
              f"afade=t=in:st=0:d=0.3,afade=t=out:st={afade:.2f}:d=1.5,dynaudnorm[a]")

    run([FFMPEG, "-y", "-v", "error", "-i", raw, "-ss", f"{start:.3f}", "-t", f"{total:.3f}",
         "-i", music, "-filter_complex", vchain + ";" + achain,
         "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", outfile])

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    if os.path.exists(raw): os.remove(raw)
    print(f"\nmontage -> {outfile}")
    print(f"  {W}x{H}@{FPS}  {dur_of(outfile):.1f}s  {len(segs)} cuts  "
          f"grade={grade}  music={os.path.basename(music)}")


if __name__ == "__main__":
    main()
