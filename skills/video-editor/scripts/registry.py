# registry.py — ARTIFACT #1: the Source Truth Panel. Index every asset in a folder so the factory
#   (and I) never forget what exists. Deterministic facts come from ffprobe (the tool's job);
#   semantic tags (role/energy/emotion/humor/hero moments) are SLOTS I fill during analysis
#   (the model's job). Re-running MERGES — your filled tags are preserved.
#     py registry.py <assets_dir> [registry.json] [--beats]
#   --beats: also run beatmap.py on audio files and store bpm/drops.
#
# registry.json:
#   { root, summary:{...counts/durations}, assets:[ {id, rel, type, ...facts, tags:{...slots}} ] }
import json, os, subprocess, sys

FFPROBE = r"C:\ffmpeg\bin\ffprobe" if os.path.exists(r"C:\ffmpeg\bin\ffprobe.exe") else "ffprobe"
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi")
IMAGE = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
AUDIO = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus")

# semantic tag slots the MODEL fills (kept stable so re-index preserves them)
TAG_SLOTS = {"role": "", "energy": None, "emotion": "", "movement": "",
             "face": None, "humor": None, "quality": None, "topic": "",
             "hero_moments": [], "use_for": [], "notes": ""}


def probe(path):
    try:
        out = subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries",
             "format=duration:stream=width,height,r_frame_rate,codec_type",
             "-of", "json", path], text=True)
        d = json.loads(out)
    except Exception as e:
        return {"error": str(e)}
    f = {"duration": round(float(d.get("format", {}).get("duration", 0) or 0), 2)}
    has_a = False
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and "width" in s:
            f["w"], f["h"] = s["width"], s["height"]
            rf = s.get("r_frame_rate", "0/1")
            try: n, dd = rf.split("/"); f["fps"] = round(int(n) / int(dd), 2) if int(dd) else None
            except Exception: f["fps"] = None
        if s.get("codec_type") == "audio": has_a = True
    if "w" in f:
        f["orientation"] = ("portrait" if f["h"] > f["w"] else
                            "landscape" if f["w"] > f["h"] else "square")
    f["has_audio"] = has_a
    return f


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args: sys.exit("usage: py registry.py <assets_dir> [registry.json] [--beats]")
    root = os.path.abspath(args[0])
    out = args[1] if len(args) > 1 else os.path.join(root, "registry.json")

    prev = {}
    if os.path.isfile(out):
        try:
            for a in json.load(open(out, encoding="utf-8")).get("assets", []):
                prev[a["rel"]] = a.get("tags", {})
        except Exception: pass

    assets = []
    for dp, _, files in os.walk(root):
        for fn in sorted(files):
            ext = os.path.splitext(fn)[1].lower()
            kind = ("video" if ext in VIDEO else "image" if ext in IMAGE
                    else "audio" if ext in AUDIO else None)
            if not kind: continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            a = {"id": rel.replace("/", "_"), "rel": rel, "type": kind,
                 "size_mb": round(os.path.getsize(full) / 1e6, 1)}
            a.update(probe(full))
            if kind == "audio" and "--beats" in flags:
                bj = os.path.splitext(full)[0] + ".beats.json"
                if not os.path.isfile(bj):
                    subprocess.run([sys.executable, os.path.join(HERE, "beatmap.py"), full, bj])
                if os.path.isfile(bj):
                    b = json.load(open(bj, encoding="utf-8"))
                    a["audio"] = {"bpm": b.get("bpm"), "drops": b.get("drops", [])[:12],
                                  "downbeats": len(b.get("downbeats", []))}
            # preserve filled tags; ensure all slots exist
            tags = dict(TAG_SLOTS); tags.update(prev.get(rel, {}))
            a["tags"] = tags
            assets.append(a)

    vids = [a for a in assets if a["type"] == "video"]
    summary = {"counts": {k: sum(1 for a in assets if a["type"] == k) for k in ("video", "image", "audio")},
               "total_video_sec": round(sum(a.get("duration", 0) for a in vids), 1),
               "tagged": sum(1 for a in assets if a["tags"].get("role"))}
    reg = {"root": root, "summary": summary, "assets": assets}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=1)
    print(f"Source Truth Panel -> {out}")
    print(f"  {summary['counts']} | video {summary['total_video_sec']}s | "
          f"{summary['tagged']}/{len(assets)} assets have a role tag")
    print("  (fill tags.role/energy/hero_moments/use_for per asset; re-run preserves them)")


if __name__ == "__main__":
    main()
