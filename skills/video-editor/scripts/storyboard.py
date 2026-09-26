# storyboard.py — assemble a narrated story from per-beat assets into one video.
#   py storyboard.py story.json
# story.json: { output:{w,h,fps,file}, music?, beats:[ {vo, visual, text?, sfx?, pad?} ] }
# Each beat: visual (video/gif/image) cover-scaled to frame, length = narration + pad,
# caption drawn, narration + sfx mixed. Beats are concatenated. ffmpeg under the hood.
import json, subprocess, sys, os

FONT = "C\\:/Windows/Fonts/arialbd.ttf"
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")

def dur_of(f):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).strip())

def esc(t): return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")
def run(c):
    if subprocess.run(c).returncode != 0: sys.exit("step failed: " + " ".join(map(str, c[:5])) + " …")

sb = json.load(open(sys.argv[1], encoding="utf-8"))
D = os.path.dirname(os.path.abspath(sys.argv[1]))
P = lambda r: r if os.path.isabs(r) else os.path.join(D, r)
o = sb.get("output", {}); W, H, FPS = o.get("w", 1920), o.get("h", 1080), o.get("fps", 30)
outfile = P(o["file"])
tmp = outfile + ".beats"; os.makedirs(tmp, exist_ok=True)

beat_files = []
for i, b in enumerate(sb["beats"]):
    vo = P(b["vo"]); vis = P(b["visual"])
    dur = round(dur_of(vo) + float(b.get("pad", 0.5)), 2)
    is_img = vis.lower().endswith(IMG_EXT)
    inp = (["-loop", "1", "-t", str(dur), "-i", vis] if is_img
           else ["-stream_loop", "-1", "-i", vis])
    inputs = inp + ["-i", vo]
    sfx = P(b["sfx"]) if b.get("sfx") else None
    if sfx: inputs += ["-i", sfx]

    # video: cover-fill the frame (no bars) + caption
    v = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
         f"fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS[vv]")
    txt = b.get("text", "")
    if txt:
        v += (f";[vv]drawtext=fontfile='{FONT}':text='{esc(txt)}':fontsize=76:fontcolor=white:"
              f"borderw=4:bordercolor=black@0.65:x=(w-tw)/2:y=h-190[v]")
        last = "v"
    else:
        last = "vv"
    # audio: narration (padded to dur) + optional sfx under it
    a = f"[1:a]apad,atrim=0:{dur},asetpts=PTS-STARTPTS[av]"
    if sfx:
        a += f";[2:a]volume=0.55,apad,atrim=0:{dur}[sv];[av][sv]amix=inputs=2:duration=first:dropout_transition=0[a]"
    else:
        a += ";[av]anull[a]"

    bf = os.path.join(tmp, f"b{i}.mp4"); beat_files.append(bf)
    run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", v + ";" + a,
         "-map", f"[{last}]", "-map", "[a]", "-t", str(dur), "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", bf])
    print(f"  beat {i+1}: {dur}s  '{txt}'  <- {os.path.basename(vis)}")

# concat
lst = os.path.join(tmp, "list.txt")
open(lst, "w").write("\n".join(f"file '{bf.replace(os.sep,'/')}'" for bf in beat_files))
run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
     "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-movflags", "+faststart", outfile])
import shutil; shutil.rmtree(tmp, ignore_errors=True)
print(f"\nstory -> {outfile}  ({W}x{H}@{FPS}, {dur_of(outfile):.1f}s, {len(beat_files)} beats)")
