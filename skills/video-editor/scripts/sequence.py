# sequence.py — hand-authored STORY cut: an explicit ordered list of beats (specific clips/images,
#   each trimmed + placed + captioned + effected), a music bed whose DROP is aligned to a chosen
#   beat, SFX on the timeline, a global grade. The narrative-control complement to montage.py
#   (beat-grid pool) and storyboard.py (TTS narration). ffmpeg under the hood.
#     py sequence.py story.json        (run with Bash sandbox OFF)
#
# story.json:
# {
#   "output": {"w":1080,"h":1920,"fps":30,"file":"out.mp4"},
#   "music": "song.mp3", "music_vol": 0.9,
#   "music_drop": 28.8, "align_beat": 5,   # shift song so its drop@28.8 lands at beat #5's start
#   "music_start": null,                    # or set explicitly (overrides align)
#   "grade": "cinematic", "vignette": true,
#   "beats": [
#     {"card":"AIKO", "sub":"a new form", "dur":2.0, "fx":["flash"]},
#     {"src":"clip.mp4", "in":40, "dur":2.5, "crop":"right", "speed":0.8,
#      "text":"It started as a 2D pixel agent", "fx":["punch"], "sfx":"whoosh"},
#     {"src":"still.jpg", "dur":1.8, "text":"it kept evolving", "fx":["kenburns"]},
#     {"credits":["Motion: Kimodo (nv-tlabs)","Avatar: Hu Tao VRM — Madoka-Senpai (VRoid Hub)"], "dur":3.0}
#   ]
# }
# fx: "kenburns"(images) "punch" "flash" "shake" "slowmo".  crop: left|center|right (landscape->portrait).
# speed: playback rate (<1 = slow-mo). sfx: name (globbed in skill assets/sfx) or path.
import json, os, sys, glob, subprocess
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # never let a unicode caption crash a render
except Exception: pass

FFMPEG = r"C:\ffmpeg\bin\ffmpeg" if os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe") else "ffmpeg"
FFPROBE = r"C:\ffmpeg\bin\ffprobe" if os.path.exists(r"C:\ffmpeg\bin\ffprobe.exe") else "ffprobe"
SFX_ROOTS = [os.path.expanduser("~/.claude/skills/video-editor/assets/sfx"),
             os.path.expanduser("~/.claude/asset-library/fx-sfx"),
             os.path.expanduser("~/.claude/asset-library/sfx-freesound")]
FONT = "C\\:/Windows/Fonts/arialbd.ttf"
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

GRADES = {
    "cinematic": "eq=contrast=1.07:saturation=1.10:brightness=0.01,curves=preset=medium_contrast",
    "warm": "eq=saturation=1.12,colorbalance=rm=.05:gm=.02:bs=-.04",
    "cold": "eq=saturation=1.05,colorbalance=rm=-.04:bs=.06",
    "vivid": "eq=contrast=1.10:saturation=1.30", "noir": "hue=s=0,eq=contrast=1.18",
    # living neon: pop the product's violet/pink/cyan, LIFT shadows so it reads alive not ominous
    "neon": "eq=contrast=1.05:saturation=1.34:brightness=0.025:gamma=1.05,colorbalance=bs=.05:rm=.02:gh=-.01",
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
        sys.exit("ffmpeg step failed:\n  " + " ".join(map(str, cmd[:6])) + " …\n" + r.stderr[-1000:])

def esc(t):
    return str(t).replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")

def sfx_path(name):
    if not name: return None
    if "/" in name or os.path.isabs(name): return name if os.path.exists(name) else None
    for root in SFX_ROOTS:
        g = glob.glob(os.path.join(root, "**", f"*{name}*"), recursive=True)
        g = [x for x in g if x.lower().endswith((".wav", ".mp3", ".ogg"))]
        if g: return g[0]
    return None


QWEN_IMG = "qwen-tts:baked"
# external voice library (21 ref voices) auto-mounted OVER the 8 baked into the image
_EXT_VOICES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "voice_actors", "english")
def synth(text, voice, outdir, name):
    """Qwen3-TTS voice-clone narration via the baked docker image -> 24k mono wav."""
    out = os.path.join(outdir, name + ".wav")
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        return out
    cmd = ["docker", "run", "--rm", "-i", "-v", f"{outdir.replace(chr(92),'/')}:/out"]
    if os.path.isdir(_EXT_VOICES):
        cmd += ["-v", f"{os.path.abspath(_EXT_VOICES).replace(chr(92),'/')}:/bundle/voice_actors/english:ro"]
    cmd += [QWEN_IMG,
           "--model", "/bundle/models/qwen-talker-0.6b-base-Q4_K_M.gguf",
           "--codec", "/bundle/models/qwen-tokenizer-12hz-Q4_K_M.gguf",
           "--lang", "english",
           "--ref-wav", f"/bundle/voice_actors/english/{voice}.wav",
           "--ref-text", f"/bundle/voice_actors/english/{voice}.txt",
           "--seed", "281", "--format", "wav16", "-o", f"/out/{name}.wav"]
    r = subprocess.run(cmd, input=text.encode("utf-8"),
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0 or not os.path.exists(out):
        print(f"  [tts] FAILED '{text[:34]}': {r.stderr.decode(errors='replace')[-160:]}", file=sys.stderr)
        return None
    return out


def caption(text, W, H):
    if not text: return ""
    fs = max(40, int(W * 0.058))
    return (f",drawtext=fontfile='{FONT}':text='{esc(text)}':fontsize={fs}:fontcolor=white:"
            f"borderw={max(3,fs//16)}:bordercolor=black@0.75:box=1:boxcolor=black@0.28:boxborderw=22:"
            f"x=(w-tw)/2:y=h*0.74:line_spacing=8")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    D = os.path.dirname(os.path.abspath(sys.argv[1]))
    P = lambda r: r if (r and os.path.isabs(r)) else os.path.join(D, r)
    o = spec.get("output", {}); W, H, FPS = o.get("w", 1080), o.get("h", 1920), o.get("fps", 30)
    outfile = P(o["file"])
    beats = spec["beats"]
    # preflight: VO needs the Qwen docker daemon. Fail LOUD instead of silently rendering vo=0
    # (a narration-less video that reports "success" is worse than an error).
    if any(b.get("vo") for b in beats):
        try:
            subprocess.run([DOCKER if 'DOCKER' in globals() else "docker", "info"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            sys.exit("[sequence] ABORT: VO beats present but the Docker daemon is unreachable "
                     "(Qwen TTS needs it). Start Docker Desktop, wait for 'docker info' to work, then re-run.")

    tmp = outfile + ".seq"; os.makedirs(tmp, exist_ok=True)
    vodir = outfile + ".vocache"; os.makedirs(vodir, exist_ok=True)  # PERSISTS across runs (keyed voice+text) — re-renders reuse VO
    seg_files, starts, cum = [], [], 0.0
    sfx_events, vo_events, native_events = [], [], []
    voice = spec.get("voice", "3_warm")
    ZN = max(2, int(0.22 * FPS))
    import hashlib

    for i, b in enumerate(beats):
        bvoice = b.get("voice", voice)                  # per-beat voice override (use the range)
        vo_wav = (synth(b["vo"], bvoice, vodir, "vo_" + hashlib.md5((bvoice + "|" + b["vo"]).encode("utf-8")).hexdigest()[:10])
                  if b.get("vo") else None)            # cache keyed on VOICE+TEXT, so edits re-synth
        if "dur" in b:                                  # explicit dur sets the FLOOR (show-time)...
            dur = round(float(b["dur"]), 3)
            if vo_wav:                                  # ...but NEVER shorter than the VO, or it bleeds
                dur = max(dur, round(dur_of(vo_wav) + float(b.get("pad", 0.4)), 3))
        elif vo_wav:
            dur = round(dur_of(vo_wav) + float(b.get("pad", 0.4)), 3)   # else VO drives length
        else:
            dur = 2.0
        starts.append(cum); cum += dur
        if vo_wav: vo_events.append((starts[i], vo_wav))
        fx = b.get("fx", [])
        sf = os.path.join(tmp, f"s{i:03d}.mp4"); seg_files.append(sf)
        _sfxv = b.get("sfx")
        if _sfxv and ("/" in _sfxv or "\\" in _sfxv) and not os.path.isabs(_sfxv):
            _sfxv = P(_sfxv)  # resolve deck-relative sfx against the seq-file dir, like src
        sx = sfx_path(_sfxv) if _sfxv else None
        if sx: sfx_events.append((starts[i], sx))

        # ---- card / credits beat (generated background) ----
        if "card" in b or "credits" in b:
            vf = "format=yuv420p"
            if "card" in b:
                ct = b['card']
                # adaptive: shrink so the line fits ~92% width (bold Arial ≈ 0.52*fs per char)
                fs = min(int(W * 0.13), int(0.92 * W / (0.52 * max(1, len(ct)))))
                vf += (f",drawtext=fontfile='{FONT}':text='{esc(ct)}':fontsize={fs}:"
                       f"fontcolor=white:x=(w-tw)/2:y=h*0.40-th/2")
                if b.get("sub"):
                    st_ = b['sub']; fss = min(int(W * 0.052), int(0.92 * W / (0.52 * max(1, len(st_)))))
                    vf += (f",drawtext=fontfile='{FONT}':text='{esc(st_)}':fontsize={fss}:"
                           f"fontcolor=0xc9c9e6:x=(w-tw)/2:y=h*0.50")
            else:
                lines = b["credits"] if isinstance(b["credits"], list) else [b["credits"]]
                fs = int(W * 0.034)
                for k, ln in enumerate(lines):
                    vf += (f",drawtext=fontfile='{FONT}':text='{esc(ln)}':fontsize={fs}:fontcolor=0xd8d8ea:"
                           f"x=(w-tw)/2:y=h*0.44+{k}*{int(fs*1.7)}")
            if "flash" in fx: vf += ",fade=t=in:st=0:d=0.10:color=0x7C5CFF"
            vf += ",fade=t=in:st=0:d=0.25"
            run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
                 f"color=c={b.get('bg','0x0b0b14')}:s={W}x{H}:d={dur}:r={FPS}", "-vf", vf,
                 "-t", str(dur), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "20", "-pix_fmt", "yuv420p", sf])
            print(f"  beat {i}: card '{b.get('card', b.get('credits'))}'  {dur}s")
            continue

        # ---- split beat: two sources shown SIMULTANEOUSLY (e.g. PC avatar + phone chat,
        #      the same session from two angles). fit=True => contain (show everything, no crop);
        #      full=True => fast-forward each whole clip; ratio => size of the first cell. ----
        if "split" in b:
            srcs = [P(s) for s in b["split"]][:2]
            ins = b.get("ins", [0, 0]); lay = b.get("layout", "v")
            fit = b.get("fit", True); fullsp = b.get("full", False); ratio = float(b.get("ratio", 0.5))
            if lay == "h":
                w0 = int(W * ratio) // 2 * 2; cells = [(w0, H), (W - w0, H)]; stk = "hstack=inputs=2"
            else:
                h0 = int(H * ratio) // 2 * 2; cells = [(W, h0), (W, H - h0)]; stk = "vstack=inputs=2"
            sin, parts = [], []
            for k, s in enumerate(srcs):
                cw, ch2 = cells[k]; in0 = t2s(ins[k] if k < len(ins) else 0)
                spd = (max(1.0, (dur_of(s) - in0) / dur) if fullsp else float(b.get("speed", 1.0)))
                sin += ["-ss", str(in0), "-t", str(round(dur * spd, 3)), "-i", s]
                sc = (f"scale={cw}:{ch2}:force_original_aspect_ratio=decrease,"
                      f"pad={cw}:{ch2}:(ow-iw)/2:(oh-ih)/2:black" if fit
                      else f"scale={cw}:{ch2}:force_original_aspect_ratio=increase,crop={cw}:{ch2}")
                pc = f"[{k}:v]{sc},setpts=PTS-STARTPTS"
                if abs(spd - 1) > 1e-3: pc += f",setpts={1.0/spd:.5f}*PTS"
                pc += f",fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS[p{k}]"
                parts.append(pc)
            tail = "[v0]format=yuv420p"
            if "flash" in fx: tail += ",fade=t=in:st=0:d=0.08:color=0x7C5CFF"
            tail += caption(b.get("text", ""), W, H) + f",trim=0:{dur},setpts=PTS-STARTPTS[v]"
            fc = ";".join(parts) + f";[p0][p1]{stk}[v0];" + tail
            run([FFMPEG, "-y", "-v", "error"] + sin + ["-filter_complex", fc, "-map", "[v]",
                 "-t", str(dur), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "20", "-pix_fmt", "yuv420p", sf])
            print(f"  beat {i}: SPLIT-{lay}{' full' if fullsp else ''} "
                  f"{os.path.basename(srcs[0])}+{os.path.basename(srcs[1])}  {dur}s")
            continue

        # ---- media beat (image or video) ----
        src = P(b["src"])
        is_img = src.lower().endswith(IMG_EXT)
        crop = b.get("crop", "center")
        pre = ""  # pre-crop landscape -> pick a half before cover-fill
        if crop == "right": pre = "crop=iw/2:ih:iw/2:0,"
        elif crop == "left": pre = "crop=iw/2:ih:0:0,"
        cover = f"{pre}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"

        if is_img:
            chain = f"{cover},fps={FPS}"
            if "kenburns" in fx:
                tot = max(2, int(dur * FPS))
                chain += (f",zoompan=z='min(zoom+0.0007,1.12)':d={tot}:"
                          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
            inp = ["-loop", "1", "-t", str(dur), "-i", src]
        else:
            speed = float(b.get("speed", 1.0))
            inpt0 = t2s(b.get("in", 0))
            if b.get("full"):  # fast-forward the WHOLE remaining clip into this beat's dur
                speed = max(1.0, (dur_of(src) - inpt0) / dur)
            need = round(dur * speed, 3)
            chain = f"{cover},setpts=PTS-STARTPTS"
            if abs(speed - 1.0) > 1e-3: chain += f",setpts={1.0/speed:.5f}*PTS"
            chain += f",fps={FPS}"
            inp = ["-ss", str(inpt0), "-t", str(need), "-i", src]

        if "shake" in fx:
            A = 14
            chain += (f",crop=iw-{2*A}:ih-{2*A}:x='{A}+{A}*sin(2*PI*t*10)':"
                      f"y='{A}+{A}*cos(2*PI*t*8)',scale={W}:{H}")
        if "punch" in fx and not is_img:
            z0 = 1.30 if "slowmo" in fx else 1.16
            chain += (f",zoompan=z='if(lte(on,{ZN}),{z0}-{z0-1:.3f}*on/{ZN},1)':"
                      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
        if "flash" in fx: chain += ",fade=t=in:st=0:d=0.08:color=0x7C5CFF"
        chain += caption(b.get("text", ""), W, H)
        # freeze-fill: if the source runs short for this slot (bad in/dur), clone the last frame
        # to fill `dur` instead of truncating — a short segment would drift the audio timeline.
        if not is_img:
            chain += f",tpad=stop_mode=clone:stop_duration={dur}"
        chain += f",trim=0:{dur},setpts=PTS-STARTPTS,format=yuv420p"

        # optional VFX overlay composited on top (particles / light-leak / glitch / sparkle)
        ov = b.get("overlay")
        enc = ["-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", "-t", str(dur), sf]
        if ov:
            osrc = P(ov["src"]); mode = ov.get("mode", "screen"); op = float(ov.get("opacity", 0.6))
            oin = (["-stream_loop", "-1"] if ov.get("loop", True) else []) + \
                  ["-ss", str(t2s(ov.get("in", 0))), "-t", str(dur), "-i", osrc]
            ofit = (f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS")
            if mode == "alpha":  # true-alpha asset (transparent gif/png-seq)
                fc = f"[0:v]{chain}[base];{ofit},format=yuva420p[ov];[base][ov]overlay=0:0[v]"
            else:                # screen/add/lighten/... blend (black-bg particles, leaks)
                fc = (f"[0:v]{chain}[base];{ofit},format=yuv420p[ov];"
                      f"[base][ov]blend=all_mode={mode}:all_opacity={op}[v]")
            run([FFMPEG, "-y", "-v", "error"] + inp + oin + ["-filter_complex", fc, "-map", "[v]"] + enc)
        else:
            run([FFMPEG, "-y", "-v", "error"] + inp + ["-an", "-vf", chain] + enc)
        print(f"  beat {i}: {'IMG' if is_img else 'VID'} {os.path.basename(src)}  {dur}s  "
              f"fx={fx}  '{b.get('text','')}'")

        # ---- native audio showcase: keep THIS clip's own audio (e.g. a voice sample) and
        #      register it as a timed event so it plays in the final mix. Give the beat no
        #      "vo" and it dominates the narration (VO pauses here). value = volume (true=1.3). ----
        na = b.get("native_audio")
        if na and not is_img:
            navol = 1.3 if na is True else float(na)
            naw = os.path.join(tmp, f"na{i:03d}.wav")
            run([FFMPEG, "-y", "-v", "error", "-ss", str(inpt0), "-t", str(dur), "-i", src,
                 "-vn", "-ac", "2", "-ar", "48000", naw])
            if os.path.exists(naw):
                native_events.append((starts[i], naw, navol))

    total = round(cum, 3)
    # ---- concat ----
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("\n".join(f"file '{f.replace(os.sep,'/')}'" for f in seg_files))
    raw = outfile + ".raw.mp4"
    run([FFMPEG, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", raw])

    # ---- music start (align a drop to a beat, or explicit) ----
    music = P(spec["music"]) if spec.get("music") else None
    mstart = spec.get("music_start")
    if music and mstart is None and spec.get("music_drop") is not None and spec.get("align_beat") is not None:
        mstart = max(0.0, t2s(spec["music_drop"]) - starts[int(spec["align_beat"])])
        print(f"  music aligned: drop {spec['music_drop']}s -> beat {spec['align_beat']} "
              f"@ {starts[int(spec['align_beat'])]:.2f}s ; music_start={mstart:.2f}s")
    mstart = float(mstart or 0.0)

    # ---- final pass: grade + vignette + music + sfx ----
    vf = []
    g = spec.get("grade")
    if g in GRADES: vf.append(GRADES[g])
    if spec.get("vignette", True): vf.append("vignette=PI/5")
    vchain = "[0:v]" + (",".join(vf) if vf else "null") + "[v]"

    inputs = ["-i", raw]; achains, amix = [], []; idx = 1
    have_vo = bool(vo_events)
    if music:
        inputs += ["-ss", f"{mstart:.3f}", "-t", f"{total:.3f}", "-i", music]
        vol = spec.get("duck", 0.26) if have_vo else spec.get("music_vol", 0.9)  # duck under narration
        achains.append(f"[{idx}:a]aresample=48000,atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol},"
                       f"afade=t=in:st=0:d=0.4,afade=t=out:st={max(0,total-1.3):.2f}:d=1.3[m]")
        amix.append("[m]"); idx += 1
    for j, (t, f) in enumerate(vo_events):
        inputs += ["-i", f]; ms = int(t * 1000)
        achains.append(f"[{idx}:a]aresample=48000,adelay={ms}|{ms},volume=1.0[vo{j}]")
        amix.append(f"[vo{j}]"); idx += 1
    for j, (t, f, v) in enumerate(native_events):
        inputs += ["-i", f]; ms = int(t * 1000)
        achains.append(f"[{idx}:a]aresample=48000,volume={v},adelay={ms}|{ms}[na{j}]")
        amix.append(f"[na{j}]"); idx += 1
    sfxvol = spec.get("sfx_vol", 0.85)
    for j, (t, f) in enumerate(sfx_events):
        inputs += ["-i", f]; ms = int(t * 1000)
        achains.append(f"[{idx}:a]aresample=48000,volume={sfxvol},adelay={ms}|{ms}[x{j}]")
        amix.append(f"[x{j}]"); idx += 1
    if amix:
        if len(amix) > 1:
            achains.append("".join(amix) + f"amix=inputs={len(amix)}:duration=longest:dropout_transition=0,"
                           f"apad,atrim=0:{total:.3f},dynaudnorm[a]")
        else:
            achains.append(f"{amix[0]}apad,atrim=0:{total:.3f}[a]")
        amap = ["-map", "[a]"]
    else:
        amap = []

    fc = vchain + ((";" + ";".join(achains)) if achains else "")
    cmd = [FFMPEG, "-y", "-v", "error"] + inputs + ["-filter_complex", fc, "-map", "[v]"] + amap + \
          ["-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if amap: cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [outfile]
    run(cmd)

    import shutil; shutil.rmtree(tmp, ignore_errors=True)
    if os.path.exists(raw): os.remove(raw)
    print(f"\nsequence -> {outfile}")
    print(f"  {W}x{H}@{FPS}  {dur_of(outfile):.1f}s  {len(beats)} beats  "
          f"vo={len(vo_events)}  sfx={len(sfx_events)}  music={'yes' if music else 'no'}  grade={g}")


if __name__ == "__main__":
    main()
