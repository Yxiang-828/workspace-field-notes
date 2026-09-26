# render.py — apply an EDL to a recording: cuts → full-screen section cards (html-deck
#              design + SFX) → music bed → 1080p export. ffmpeg under the hood.
#   py render.py edit.json        (run with Bash sandbox OFF — cards load Google Fonts)
# EDL: { source, output:{w,h,fps,file}, music, cuts:[{from,to}], markers:[{at,title,sfx}] }
# Times "1:10.5"/"0:32"/12.5 (seconds), SOURCE-time, auto-remapped across cuts.
import json, subprocess, sys, os, glob

SFXROOT = os.path.expanduser("~/.claude/skills/video-editor/assets/sfx")
MAKECARDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "make-cards.mjs")
CARD_DUR, FADE = 1.9, 0.28

def t2s(t):
    if isinstance(t, (int, float)): return float(t)
    s = 0.0
    for p in str(t).split(":"): s = s * 60 + float(p)
    return s

def dur_of(f):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).strip())

def run(cmd, **k):
    if subprocess.run(cmd, **k).returncode != 0: sys.exit("step failed: " + " ".join(map(str, cmd[:4])) + " …")

edl = json.load(open(sys.argv[1], encoding="utf-8"))
D = os.path.dirname(os.path.abspath(sys.argv[1]))
P = lambda rel: rel if os.path.isabs(rel) else os.path.join(D, rel)
src = P(edl["source"])
o = edl.get("output", {}); W, H, FPS = o.get("w", 1920), o.get("h", 1080), o.get("fps", 30)
outfile = P(o.get("file", "final.mp4"))

dur = dur_of(src)
cuts = sorted((t2s(c["from"]), t2s(c["to"])) for c in edl.get("cuts", []))
kept, pos = [], 0.0
for a, b in cuts:
    if a > pos: kept.append((pos, a))
    pos = max(pos, b)
if pos < dur - 0.05: kept.append((pos, dur))
if not kept: kept = [(0.0, dur)]

def remap(ts):
    ot = 0.0
    for a, b in kept:
        if ts >= b: ot += b - a
        elif ts >= a: return ot + (ts - a)
        else: return ot
    return ot

# ---- PASS 1: cuts (trim + concat) ----
work = src
if len(kept) > 1 or kept[0] != (0.0, dur):
    vt = [f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}]" for i, (a, b) in enumerate(kept)]
    at = [f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}]" for i, (a, b) in enumerate(kept)]
    cc = "".join(f"[v{i}][a{i}]" for i in range(len(kept)))
    filt = ";".join(vt + at) + f";{cc}concat=n={len(kept)}:v=1:a=1[v][a]"
    work = outfile + ".cut.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", filt,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", work])

# ---- generate full-screen section cards (html-deck design) ----
markers = edl.get("markers", [])
cards = []
if markers:
    cdir = outfile + ".cards"; os.makedirs(cdir, exist_ok=True)
    spec = [{"title": m.get("title", ""), "file": os.path.join(cdir, f"c{i}.png").replace("\\", "/")}
            for i, m in enumerate(markers)]
    cj = outfile + ".cards.json"; open(cj, "w", encoding="utf-8").write(json.dumps(spec))
    run(["node", MAKECARDS, cj])
    cards = [s["file"] for s in spec]

# ---- resolve marker SFX + music ----
def sfx_path(m):
    s = m.get("sfx", "")
    if not s: return None
    if "/" in s or os.path.isabs(s): return P(s)
    g = glob.glob(os.path.join(SFXROOT, "**", f"*{s}*"), recursive=True)
    return g[0] if g else None
sfx = [(remap(t2s(m["at"])), f) for m in markers if (f := sfx_path(m)) and os.path.exists(f)]
music = P(edl["music"]) if edl.get("music") else None
if music and not os.path.exists(music): music = None

# ---- PASS 2: scale/pad base + card overlays (video); sfx + music (audio) ----
inputs = ["-i", work]
for c in cards: inputs += ["-loop", "1", "-t", str(CARD_DUR + 0.2), "-i", c]
sfx0 = 1 + len(cards)
for _, f in sfx: inputs += ["-i", f]
mus_idx = (sfx0 + len(sfx)) if music else None
if music: inputs += ["-i", music]

vf = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,fps={FPS}[vs]"
last = "vs"
for i, m in enumerate(markers):
    t = remap(t2s(m["at"]))
    vf += (f";[{1+i}:v]format=yuva420p,fade=t=in:st=0:d={FADE}:alpha=1,"
           f"fade=t=out:st={CARD_DUR-FADE}:d={FADE}:alpha=1,setpts=PTS+{t}/TB[c{i}]")
    vf += f";[{last}][c{i}]overlay=0:0:enable='between(t,{t:.2f},{t+CARD_DUR:.2f})'[ov{i}]"; last = f"ov{i}"

amix_in, af = ["[0:a]"], []
for j, (t, f) in enumerate(sfx):
    ms = int(t * 1000); af.append(f"[{sfx0+j}:a]adelay={ms}|{ms}[s{j}]"); amix_in.append(f"[s{j}]")
if mus_idx is not None:
    af.append(f"[{mus_idx}:a]volume=0.12,aloop=loop=-1:size=2000000000[mus]"); amix_in.append("[mus]")
af.append(("".join(amix_in) + f"amix=inputs={len(amix_in)}:duration=first:dropout_transition=0,dynaudnorm[aout]")
          if len(amix_in) > 1 else "[0:a]anull[aout]")

run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", vf + ";" + ";".join(af),
     "-map", f"[{last}]", "-map", "[aout]", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
     "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", outfile])

# cleanup intermediates
for p in ([work] if work != src else []) + ([outfile + ".cards.json"] if markers else []):
    if os.path.exists(p): os.remove(p)
import shutil
if markers and os.path.isdir(outfile + ".cards"): shutil.rmtree(outfile + ".cards", ignore_errors=True)

print(f"rendered -> {outfile}")
print(f"  {W}x{H}@{FPS}  {dur_of(outfile):.1f}s  ({len(cuts)} cuts, {len(markers)} section cards, "
      f"{len(sfx)} sfx, music={'yes' if music else 'no'})")
