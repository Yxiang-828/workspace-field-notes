#!/usr/bin/env python3
"""image-gen: generate bespoke imagery by delegating to a local agentic CLI.

The CLIs (agy/Antigravity, codex) render images to disk via their own image tools — they do
NOT emit images on stdout. So we tell the CLI to SAVE to an exact path, then read that file.

Verified: `agy` produces a real PNG via `-p`. `codex` is a fallback.

    py gen.py --prompt "a glowing dinosaur emblem, flat vector, dark bg" --out art.png
"""
import argparse, os, subprocess, sys

MIN_BYTES = 1000  # a real image is bigger than any stray text file


def _ok(out):
    return os.path.exists(out) and os.path.getsize(out) >= MIN_BYTES


def run_agy(prompt, out, timeout):
    out_uri = os.path.abspath(out).replace(os.sep, "/")
    wrapped = (f"Use your image-generation tool to create ONE image: {prompt}. "
               f"Save the generated image file to EXACTLY this path: {out_uri} . "
               f"Reply only with the path once saved.")
    subprocess.run(["agy", "--dangerously-skip-permissions", "-p", wrapped],
                   input="", capture_output=True, text=True, timeout=timeout,
                   shell=(os.name == "nt"))
    return _ok(out)


def run_codex(prompt, out, timeout):
    out_uri = os.path.abspath(out).replace(os.sep, "/")
    wrapped = (f"Generate one image: {prompt}. Save the image file to EXACTLY: {out_uri}")
    subprocess.run(["codex", "exec", "--skip-git-repo-check", wrapped],
                   input="", capture_output=True, text=True, timeout=timeout,
                   shell=(os.name == "nt"))
    return _ok(out)


def main():
    ap = argparse.ArgumentParser(description="Generate an image via a local agentic CLI.")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--provider", default="agy", choices=["agy", "codex"])
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    try:
        os.remove(a.out)
    except OSError:
        pass

    order = [a.provider] + [p for p in ("agy", "codex") if p != a.provider]
    for prov in order:
        fn = run_agy if prov == "agy" else run_codex
        try:
            if fn(a.prompt, a.out, a.timeout):
                print(a.out)
                return 0
            sys.stderr.write(f"[{prov}] produced no image; trying next\n")
        except subprocess.TimeoutExpired:
            sys.stderr.write(f"[{prov}] timed out\n")
        except FileNotFoundError:
            sys.stderr.write(f"[{prov}] not installed\n")
    sys.stderr.write("ERROR: no provider produced an image\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
