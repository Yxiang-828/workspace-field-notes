#!/usr/bin/env python3
"""Robust Qwen3-TTS: synth sentence-by-sentence (short chunks don't loop),
sanity-check each chunk's duration vs word count, retry on blow-ups, concat.
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qwen_say import synth as _synth

def _dur(f):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of",
                        "default=noprint_wrappers=1:nokey=1", f], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except: return 0.0

def _chunks(text):
    # split on sentence enders, keep them short; further split very long clauses on commas
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    out = []
    for p in parts:
        p = p.strip()
        if not p: continue
        if len(p.split()) > 14:                       # long clause -> split on commas
            sub = [s.strip() for s in p.split(',') if s.strip()]
            out.extend(sub)
        else:
            out.append(p)
    return out

def synth_safe(text, voice, out, voices_seed=281):
    """Returns out path. Each chunk validated: a chunk should be < words*1.1 + 3.5 s.
    On blow-up, retry with alternate seeds; if still bad, skip that chunk."""
    workdir = os.path.dirname(os.path.abspath(out))
    base = os.path.splitext(os.path.basename(out))[0]
    chunk_files = []
    for ci, ch in enumerate(_chunks(text)):
        nwords = len(ch.split())
        ceiling = nwords * 1.1 + 3.5
        cf = os.path.join(workdir, f"{base}_c{ci}.wav")
        good = None
        for seed in (voices_seed, 7, 4242, 99):
            if os.path.exists(cf): os.remove(cf)
            _synth(ch, voice, cf, seed=seed)
            if os.path.exists(cf):
                d = _dur(cf)
                if 0.3 < d <= ceiling:
                    good = cf; break
                print(f"    [retry] chunk {ci} seed {seed}: {d:.1f}s > ceil {ceiling:.1f}s '{ch[:40]}'")
        if good:
            chunk_files.append(good)
        else:
            print(f"    [skip] chunk {ci} never stabilized: '{ch[:50]}'")
    if not chunk_files:
        return None
    if len(chunk_files) == 1:
        os.replace(chunk_files[0], out); return out
    # concat with a tiny 0.18s gap between chunks
    lst = os.path.join(workdir, f"{base}_list.txt")
    gap = os.path.join(workdir, "_gap.wav")
    if not os.path.exists(gap):
        subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i",
                        "anullsrc=r=24000:cl=mono","-t","0.18", gap], capture_output=True)
    with open(lst,"w") as f:
        for k,cf in enumerate(chunk_files):
            f.write(f"file '{cf.replace(os.sep,'/')}'\n")
            if k < len(chunk_files)-1: f.write(f"file '{gap.replace(os.sep,'/')}'\n")
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",lst,
                    "-c","copy", out], capture_output=True)
    if not os.path.exists(out):  # fallback: re-encode concat
        subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",lst,
                        "-ar","24000","-ac","1", out], capture_output=True)
    for cf in chunk_files:
        try: os.remove(cf)
        except: pass
    return out if os.path.exists(out) else None

if __name__ == "__main__":
    # quick self-test on the line that looped
    t = ("Each of us brings our own agent. Claude, Codex, Gemini. Running locally, "
         "on a subscription we already pay for. No A P I keys. No per token bill.")
    o = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_test", "safe07.wav")
    os.makedirs(os.path.dirname(o), exist_ok=True)
    synth_safe(t, "15_soothing_woman", o)
    print("RESULT", o, _dur(o), "s")
