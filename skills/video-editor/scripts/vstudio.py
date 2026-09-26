#!/usr/bin/env python3
"""
vstudio — multi-project workspace manager for the video-editor skill.

Each project is a self-contained folder with input/ work/ output/ + a spec
(edit.json or story.json) + project.json metadata. The heavy media lives off
OneDrive under ~/.claude/video-studio (override with $VSTUDIO_ROOT); the skill
source (this script, render.py, ingest.sh, templates) stays tracked in the repo.

Commands
  vstudio new <name> [--source PATH] [--kind edit|story]   scaffold a project
  vstudio list                                             table of all projects
  vstudio info <name>                                      show one project
  vstudio import <file...>                                 copy raw files into _inbox/
  vstudio register <name> --output PATH [--source PATH]    adopt existing files (no move)
                          [--edit PATH] [--kind edit|story]
  vstudio ingest <name>                                    run ingest.sh on the input
  vstudio render <name>                                    run render.py / storyboard.py -> output/
  vstudio path <name>                                      print the project dir

All paths in a project's spec are absolute and point inside the project, so
render.py / storyboard.py run unchanged.
"""
import argparse, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS   = os.path.join(SKILL_DIR, "scripts")
TEMPLATES = os.path.join(SKILL_DIR, "templates")
STORE     = os.environ.get("VSTUDIO_ROOT") or os.path.expanduser("~/video-studio")
PROJECTS  = os.path.join(STORE, "projects")
INBOX     = os.path.join(STORE, "_inbox")
ASSETS    = os.path.expanduser("~/.claude/asset-library")

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".m4v")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def slug(s):
    return re.sub(r"[^a-z0-9._-]+", "-", s.strip().lower()).strip("-") or "project"

def pdir(name):
    return os.path.join(PROJECTS, slug(name))

def load_meta(d):
    p = os.path.join(d, "project.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None

def save_meta(d, meta):
    meta["updated"] = now()
    with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

def ensure_store():
    for d in (PROJECTS, INBOX):
        os.makedirs(d, exist_ok=True)

def template(kind):
    f = os.path.join(TEMPLATES, f"{kind}.template.json")
    with open(f, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_new(a):
    ensure_store()
    d = pdir(a.name)
    if os.path.exists(d) and not a.force:
        sys.exit(f"project '{slug(a.name)}' already exists ({d}); use --force to overwrite")
    for sub in ("input", "work", "output"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)

    source_in_proj = None
    if a.source:
        src = os.path.abspath(a.source)
        if not os.path.isfile(src):
            sys.exit(f"source not found: {src}")
        dst = os.path.join(d, "input", os.path.basename(src))
        if a.move:
            shutil.move(src, dst)
        elif a.link:
            try:
                if os.path.exists(dst): os.remove(dst)
                os.symlink(src, dst)
            except OSError:
                shutil.copy2(src, dst)
        else:
            shutil.copy2(src, dst)
        source_in_proj = dst

    kind = a.kind
    spec = template(kind)
    spec_name = {"edit": "edit.json", "story": "story.json",
                 "montage": "montage.json", "sequence": "sequence.json"}[kind]
    out_file = os.path.join(d, "output", f"{slug(a.name)}.mp4")
    if kind == "edit":
        spec["source"] = source_in_proj or "<put source path here>"
        spec.setdefault("output", {})["file"] = out_file
    elif kind in ("montage", "sequence"):
        if source_in_proj: spec["music"] = source_in_proj   # --source = the song
        spec.setdefault("output", {})["file"] = out_file
    else:
        spec["output"] = out_file
    with open(os.path.join(d, spec_name), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    meta = {
        "name": slug(a.name), "kind": kind, "created": now(),
        "source": source_in_proj, "spec": spec_name,
        "output": out_file, "status": "new", "notes": a.notes or "",
    }
    save_meta(d, meta)
    print(f"created {d}")
    print(f"  spec:   {os.path.join(d, spec_name)}")
    print(f"  input:  {os.path.join(d, 'input')}")
    print(f"  output: {os.path.join(d, 'output')}")
    if not source_in_proj:
        print("  (no --source given; drop a recording into input/ and set the spec source)")


def cmd_register(a):
    """Adopt already-rendered/scattered files into a project WITHOUT moving them."""
    ensure_store()
    d = pdir(a.name)
    for sub in ("input", "work", "output"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    meta = load_meta(d) or {"name": slug(a.name), "created": now(), "status": "rendered"}
    meta["kind"] = a.kind
    if a.source: meta["source"] = os.path.abspath(a.source)
    if a.output: meta["output"] = os.path.abspath(a.output)
    if a.edit:
        dst = os.path.join(d, os.path.basename(a.edit))
        shutil.copy2(os.path.abspath(a.edit), dst)
        meta["spec"] = os.path.basename(a.edit)
    meta.setdefault("status", "rendered")
    meta["registered_in_place"] = True
    save_meta(d, meta)
    print(f"registered '{slug(a.name)}' -> {d} (files left in place)")


def cmd_import(a):
    ensure_store()
    for f in a.files:
        src = os.path.abspath(f)
        if not os.path.isfile(src):
            print(f"skip (not a file): {src}"); continue
        shutil.copy2(src, os.path.join(INBOX, os.path.basename(src)))
        print(f"-> _inbox/{os.path.basename(src)}")


def cmd_list(a):
    ensure_store()
    rows = []
    for name in sorted(os.listdir(PROJECTS)):
        d = os.path.join(PROJECTS, name)
        if not os.path.isdir(d): continue
        m = load_meta(d) or {}
        out = m.get("output") or ""
        has_out = "yes" if out and os.path.isfile(out) else "-"
        rows.append((name, m.get("kind", "?"), m.get("status", "?"), has_out,
                     os.path.basename(m.get("source") or "") or "-"))
    if not rows:
        print(f"(no projects yet in {PROJECTS})"); return
    w = max(len(r[0]) for r in rows)
    print(f"{'PROJECT':<{w}}  KIND   STATUS     OUT  SOURCE")
    for n, k, s, o, src in rows:
        print(f"{n:<{w}}  {k:<5}  {s:<9}  {o:<3}  {src}")
    print(f"\nstore: {STORE}")


def cmd_info(a):
    d = pdir(a.name)
    m = load_meta(d)
    if not m: sys.exit(f"no such project: {slug(a.name)}")
    print(json.dumps(m, indent=2))
    print(f"\ndir: {d}")
    for sub in ("input", "work", "output"):
        p = os.path.join(d, sub)
        items = os.listdir(p) if os.path.isdir(p) else []
        print(f"  {sub}/: {len(items)} item(s)")


def cmd_path(a):
    print(pdir(a.name))


def _primary_input(d, meta):
    src = meta.get("source")
    if src and os.path.isfile(src):
        return src
    indir = os.path.join(d, "input")
    vids = [os.path.join(indir, f) for f in os.listdir(indir)
            if f.lower().endswith(VIDEO_EXT)] if os.path.isdir(indir) else []
    return vids[0] if vids else None


def cmd_ingest(a):
    d = pdir(a.name); m = load_meta(d)
    if not m: sys.exit(f"no such project: {slug(a.name)}")
    src = _primary_input(d, m)
    if not src: sys.exit("no input video found (drop one in input/ or set source)")
    work = os.path.join(d, "work")
    print(f"ingesting {src} -> {work}/")
    # ingest.sh writes <video>_ingest next to the video; run it from work/ on a copy ref
    r = subprocess.run(["bash", os.path.join(SKILL_DIR, "ingest.sh"), src],
                       cwd=work)
    if r.returncode == 0:
        m["status"] = "ingested"; save_meta(d, m)
    sys.exit(r.returncode)


def cmd_render(a):
    d = pdir(a.name); m = load_meta(d)
    if not m: sys.exit(f"no such project: {slug(a.name)}")
    spec = os.path.join(d, m.get("spec", "edit.json"))
    if not os.path.isfile(spec): sys.exit(f"spec not found: {spec}")

    # ---- production gate: the render (persistent state) is blocked until the cut has passed
    #      through every compulsory decision layer with reasoning (factory.py). --force bypasses. ----
    if not getattr(a, "force", False):
        dec = os.path.join(d, "decisions.json")
        sys.path.insert(0, SCRIPTS)
        import factory
        if not os.path.isfile(dec):
            sys.exit("BLOCKED by production gate: no decisions.json.\n"
                     f"  py {os.path.join(SCRIPTS,'factory.py')} new \"{dec}\"\n"
                     "  ...fill every layer (applies + reason, + decision if it applies)...\n"
                     f"  py {os.path.join(SCRIPTS,'factory.py')} check \"{dec}\"\n"
                     "  then re-run render (or pass --force to skip the gate).")
        miss = factory._validate(json.load(open(dec, encoding="utf-8")))
        if miss:
            print("BLOCKED by production gate - unresolved layers:")
            for k, why in miss: print(f"   - [{k}] {why}")
            sys.exit(f"resolve them in {dec} (or --force to bypass).")
        print("production gate: APPROVED (all decision layers passed)")

    script = {"edit": "render.py", "story": "storyboard.py",
              "montage": "montage.py", "sequence": "sequence.py"}.get(m.get("kind"), "render.py")
    print(f"rendering {m['name']} via {script}  ({spec})")
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), spec], cwd=d)
    if r.returncode == 0:
        m["status"] = "rendered"; save_meta(d, m)
        print(f"output -> {m.get('output')}")
    sys.exit(r.returncode)


def main():
    p = argparse.ArgumentParser(prog="vstudio", description="video-editor multi-project workspace")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new"); n.add_argument("name")
    n.add_argument("--source"); n.add_argument("--kind", choices=["edit", "story", "montage", "sequence"], default="edit")
    n.add_argument("--link", action="store_true", help="symlink source instead of copy")
    n.add_argument("--move", action="store_true", help="move source into the project instead of copy")
    n.add_argument("--notes", default=""); n.add_argument("--force", action="store_true")
    n.set_defaults(func=cmd_new)

    r = sub.add_parser("register"); r.add_argument("name")
    r.add_argument("--output"); r.add_argument("--source"); r.add_argument("--edit")
    r.add_argument("--kind", choices=["edit", "story", "montage", "sequence"], default="edit")
    r.set_defaults(func=cmd_register)

    im = sub.add_parser("import"); im.add_argument("files", nargs="+"); im.set_defaults(func=cmd_import)
    sub.add_parser("list").set_defaults(func=cmd_list)
    i = sub.add_parser("info"); i.add_argument("name"); i.set_defaults(func=cmd_info)
    pa = sub.add_parser("path"); pa.add_argument("name"); pa.set_defaults(func=cmd_path)
    g = sub.add_parser("ingest"); g.add_argument("name"); g.set_defaults(func=cmd_ingest)
    rn = sub.add_parser("render"); rn.add_argument("name")
    rn.add_argument("--force", action="store_true", help="bypass the production decision gate")
    rn.set_defaults(func=cmd_render)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
