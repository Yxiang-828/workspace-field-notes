# factory.py - the AI Video Factory OS. A cut moves down a production LINE of compulsory decision
#   layers; the render (persistent product) is BLOCKED until every layer has a recorded
#   decision + reasoning (a justified SKIP counts). The point: an AI forgets, so every invisible
#   editorial decision is converted into an explicit, persistent artifact later stages can read.
#
#   Tools do the deterministic spine (index, beats, assemble, validate); the MODEL does the
#   judgment (tag semantics, predict attention, simulate viewers) and WRITES it into the artifacts.
#
#   Three persistent artifacts (the AI's external brain, survive between passes):
#     1. Source Truth Panel   -> registry.py  (what exists)
#     2. Layered Timeline State-> the sequence/montage spec (+ `factory.py timeline`)  (what happens each beat)
#     3. Decision Log         -> decisions.json (+ `factory.py log`)  (why each choice was made)
#
#   py factory.py layers                       # print the production line
#   py factory.py new   decisions.json         # scaffold a decision sheet (+ objective weights + artifact slots)
#   py factory.py check decisions.json         # gate: every compulsory layer needs applies+reason (+decision)
#   py factory.py report decisions.json        # human pass summary
#   py factory.py log   decisions.json [out.md]# write the Decision Log artifact (markdown)
#   py factory.py timeline sequence.json [registry.json]   # print the Layered Timeline State
import json, os, sys

# ---- the production line (ordered). intake/asset_analysis/export bind to the 3 artifacts. ----
LAYERS = [
 ("intake",       "Intake / Source Truth", "Are ALL sources indexed + tagged in a registry (artifact #1)?",
    ["registry.py over the assets dir", "facts (ffprobe) + semantic tags (role/energy/hero/use_for)", "target platform + constraints"],
    ["registry.py", "ffprobe"]),
 ("objective",    "Objective & weights",   "Why does this video exist? Priority weights (retention/entertain/inform/convert/...).",
    ["pick primary goal", "weight 0-10 per axis", "these weights arbitrate later trade-offs"], []),
 ("story",        "Story architecture",    "Block skeleton: hook->...->payoff->CTA. Order + snippet-vs-full.",
    ["choose skeleton", "hook in <2s", "build into the drop", "payoff = the point"], []),
 ("prioritize",   "Prioritize & emphasize","Which 1-2 features are the HERO? Beats are NOT equal — give the hero disproportionate time + emphasis; compress the rest.",
    ["name hero feature(s)", "hero gets the MOST screen time", "emphasis = slow-mo / drop-to-real-time-inside-a-fast-section / hold / punch-in",
     "even a fast montage slows on its single key moment", "compress connective/secondary beats", "cut darlings that don't serve the hero"], []),
 ("asset_analysis","Asset analysis",       "Does each chosen asset's registry tag justify its slot (energy/emotion/hero)?",
    ["map registry roles -> beats", "prefer high-quality/high-energy for hooks", "reject off-tone assets"],
    ["registry.json"]),
 ("music_beat",   "Music & beat grid",     "Track chosen, analyzed; beat nodes + drop aligned to the key beat?",
    ["pick track (BPM/build-drop)", "beatmap.py", "align drop->reveal/punchline", "cut on beats", "license"],
    ["Jamendo", "archive.org/yt-dlp", "librosa"]),
 ("pacing",       "Pacing",                "Cut rhythm vs energy: fast on hype, hold on calm, accelerate into drop.",
    ["cuts/beat by section", "min_cut", "vary deliberately"], []),
 ("attention",    "Attention prediction",  "Per segment: will the viewer disengage? Mark retention-risk + the fix.",
    ["score risk per beat", "flag boredom spikes", "first 2s must hook", "trigger optional layers on high risk"], []),
 ("allocation",   "Source allocation",     "Which asset serves which beat/purpose (the allocation map)?",
    ["hook asset", "explanation asset", "payoff asset", "fluff/meme asset", "CTA asset"], []),
 ("transitions",  "Transitions",           "Per join: hardcut/flash/whip/dissolve/glitch/match/meme-interrupt?",
    ["hardcut on beat", "flash/zoom on drop", "dissolve on calm", "justify anything fancy"], []),
 ("effects",      "Camera/time effects",   "zoom-punch/shake/rgb/speed-ramp/slow-mo/freeze/ken-burns?",
    ["punch on cuts", "slow-mo hero on drop", "ken-burns stills"], []),
 ("overlays",     "VFX overlays",          "Composite particles/light-leak/glitch/bokeh/sparkle (blend+opacity)?",
    ["spell FX on skills", "leak/bokeh on reveal", "glitch on hard transition"],
    ["Pixabay/Pexels video", "Giphy/Tenor (alpha)"]),
 ("color",        "Color / look",          "Global grade + vignette/grain/LUT?",
    ["grade preset", "vignette", "grain?", "LUT?"], []),
 ("sound",        "Sound design",          "SFX per beat: riser->drop, impact on hit, whoosh, blip, shimmer?",
    ["riser into drop", "impact on reveal", "whoosh on cut", "shimmer on skill"],
    ["Freesound CC0", "BigSoundBank", "Kenney"]),
 ("captions",     "Captions / subtitles",  "Title cards, per-beat captions, auto-subtitles, emphasis style?",
    ["hook/title card", "per-beat caption", "subtitle style", "auto-subs from transcript"],
    ["Whisper"]),
 ("memes",        "Memes / reactions",     "Reaction GIFs / meme SFX - do they serve the objective + fit tone?",
    ["why (boredom/joke/trend/shock)", "intensity", "timing", "or skip (tone)"],
    ["Giphy", "Tenor", "MyInstants"]),
 ("comedy",       "Comedy / tone",         "Is humor appropriate? Type + placement without tone-breaking?",
    ["deadpan/absurd/reaction/meta", "placement", "avoid undermining serious beats"], []),
 ("voiceover",    "Voiceover / TTS",       "Provided VO / TTS / none? Time beats to the VO?",
    ["user script", "Qwen3-TTS", "music-only"],
    ["Qwen3-TTS", "ElevenLabs"]),
 ("simulation",   "Viewer simulation",     "Role-play 3-4 personas: where/why would each skip? Predicted drop-off map.",
    ["scroller", "interested", "anti-cringe", "already-knows", "-> predicted dropoff + fixes"], []),
 ("credits",      "Credits & licensing",   "Attribution + license clearance for every borrowed asset?",
    ["avatar/model", "motion/tech", "music CC", "publish-safe?"], []),
 ("validation",   "Validation",            "Technical + creative + platform checks pass?",
    ["aspect/fps/loudness/faststart", "objective satisfied", "tone consistent", "platform specs"],
    ["ffprobe"]),
 ("export_log",   "Export decision log",   "Is the Decision Log (artifact #3) written so next time = 'do what worked'?",
    ["factory.py log -> .md", "record rejected candidates + why"], []),
]
COMPULSORY = {k for k, *_ in LAYERS}
OBJ_AXES = ["retention", "entertainment", "information", "inspiration", "conversion", "brand"]


def cmd_layers(_a=None):
    print("AI VIDEO FACTORY - production line (every cut passes through these gates):\n")
    for i, (k, title, q, subs, apis) in enumerate(LAYERS, 1):
        print(f"{i:2}. [{k}] {title}\n     ? {q}\n     - {', '.join(subs)}")
        if apis: print(f"     - APIs/tools: {', '.join(apis)}")
        print()
    print("Artifacts that persist between passes:")
    print("  1) Source Truth Panel  = registry.json   2) Layered Timeline State = the spec")
    print("  3) Decision Log        = decisions.json (+ exported .md)")


def cmd_new(a):
    sheet = {"project": os.path.splitext(os.path.basename(a.path))[0], "pass": 0,
             "artifacts": {"registry": "", "spec": "", "decision_log": ""},
             "objective": {ax: 0 for ax in OBJ_AXES},
             "layers": {k: {"applies": None, "decision": "", "reason": "", "rejected": []}
                        for k, *_ in LAYERS}}
    json.dump(sheet, open(a.path, "w", encoding="utf-8"), indent=2)
    print(f"scaffolded -> {a.path}\n  set objective weights; fill every layer applies+reason "
          f"(+decision if applies); point artifacts.registry at your Source Truth Panel.")


def _validate(sheet):
    layers = sheet.get("layers", {}); miss = []
    for k, title, *_ in LAYERS:
        L = layers.get(k)
        if not L: miss.append((k, "layer absent")); continue
        ap = L.get("applies")
        if ap not in (True, False): miss.append((k, "applies must be true/false")); continue
        if not str(L.get("reason", "")).strip(): miss.append((k, "reason required (justify skips too)")); continue
        if ap is True and not str(L.get("decision", "")).strip(): miss.append((k, "applies=true but no decision"))
    # artifact bindings
    if layers.get("intake", {}).get("applies"):
        reg = sheet.get("artifacts", {}).get("registry", "")
        if not reg or not os.path.isfile(reg): miss.append(("intake", f"registry artifact missing/not found: {reg or '(unset)'}"))
    if not any(v for v in sheet.get("objective", {}).values()):
        miss.append(("objective", "set at least one priority weight > 0"))
    return miss


def cmd_check(a):
    sheet = json.load(open(a.path, encoding="utf-8"))
    miss = _validate(sheet); total = len(COMPULSORY)
    if miss:
        print(f"NOT APPROVED - {total-len([m for m in miss if m[0] in COMPULSORY])}/{total} layers ok. Blocking:")
        for k, why in miss: print(f"   - [{k}] {why}")
        sys.exit(1)
    ap = sum(1 for k in COMPULSORY if sheet["layers"][k].get("applies"))
    w = sheet.get("objective", {})
    top = ", ".join(f"{k}:{v}" for k, v in sorted(w.items(), key=lambda x: -x[1]) if v)
    print(f"APPROVED - {total}/{total} layers passed ({ap} applied, {total-ap} skipped). Objective[{top}]. Render cleared.")


def cmd_report(a):
    sheet = json.load(open(a.path, encoding="utf-8"))
    print(f"PRODUCTION REPORT - {sheet.get('project','?')} (pass {sheet.get('pass',0)})")
    w = sheet.get("objective", {})
    print("objective: " + ", ".join(f"{k}={v}" for k, v in sorted(w.items(), key=lambda x: -x[1]) if v) + "\n")
    for k, title, *_ in LAYERS:
        L = sheet.get("layers", {}).get(k, {}); ap = L.get("applies")
        mark = "[x]" if ap is True else ("- " if ap is False else "[?]")
        print(f"{mark} {title}: {L.get('decision') or ('(skip)' if ap is False else '(undecided)')}")
        if L.get("reason"): print(f"      why: {L['reason']}")
        if L.get("rejected"): print(f"      rejected: {'; '.join(L['rejected'])}")


def cmd_log(a):
    sheet = json.load(open(a.path, encoding="utf-8"))
    out = a.out or (os.path.splitext(a.path)[0] + "_log.md")
    w = sheet.get("objective", {})
    lines = [f"# Decision Log - {sheet.get('project','?')}", "",
             "**Objective:** " + ", ".join(f"{k} {v}" for k, v in sorted(w.items(), key=lambda x: -x[1]) if v),
             "**Artifacts:** " + ", ".join(f"{k}={v}" for k, v in sheet.get("artifacts", {}).items() if v), ""]
    for k, title, *_ in LAYERS:
        L = sheet.get("layers", {}).get(k, {}); ap = L.get("applies")
        tag = "APPLIED" if ap is True else ("SKIPPED" if ap is False else "?")
        lines.append(f"### {title} - {tag}")
        if L.get("decision"): lines.append(f"- decision: {L['decision']}")
        if L.get("reason"): lines.append(f"- why: {L['reason']}")
        if L.get("rejected"): lines.append(f"- rejected: {'; '.join(L['rejected'])}")
        lines.append("")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"Decision Log -> {out}  (reuse next time: 'do what worked')")


def cmd_timeline(a):
    spec = json.load(open(a.path, encoding="utf-8"))
    roles = {}
    if a.registry and os.path.isfile(a.registry):
        reg = json.load(open(a.registry, encoding="utf-8")); root = reg["root"]
        for asset in reg["assets"]:
            roles[os.path.normpath(os.path.join(root, asset["rel"])).lower()] = asset["tags"].get("role", "")
    beats = spec.get("beats", spec.get("clips", []))
    print(f"LAYERED TIMELINE STATE - {os.path.basename(a.path)}  ({len(beats)} beats)")
    print(f"{'t':>6}  {'dur':>4}  layers")
    t = 0.0
    for i, b in enumerate(beats):
        d = float(b.get("dur", 0)); src = b.get("src", "")
        role = roles.get(os.path.normpath(src).lower(), "") if src else ""
        tracks = []
        if b.get("card") or b.get("credits"): tracks.append("CARD")
        if src: tracks.append("V:" + (role or os.path.basename(src)))
        if b.get("text"): tracks.append(f"CAP:'{b['text'][:28]}'")
        if b.get("fx"): tracks.append("FX:" + "+".join(b["fx"]))
        if b.get("overlay"): tracks.append("OVL:" + os.path.basename(b["overlay"].get("src", "")))
        if b.get("sfx"): tracks.append("SFX:" + str(b["sfx"]))
        if b.get("risk") is not None: tracks.append(f"RISK:{b['risk']}")
        print(f"{t:6.1f}  {d:4.1f}  " + " | ".join(tracks))
        t += d
    print(f"total {t:.1f}s")


def main():
    import argparse
    p = argparse.ArgumentParser(prog="factory", description="AI video factory - decision gate + artifacts")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("layers").set_defaults(func=cmd_layers)
    for c in ("new", "check", "report"):
        sp = sub.add_parser(c); sp.add_argument("path")
        sp.set_defaults(func={"new": cmd_new, "check": cmd_check, "report": cmd_report}[c])
    lg = sub.add_parser("log"); lg.add_argument("path"); lg.add_argument("out", nargs="?"); lg.set_defaults(func=cmd_log)
    tl = sub.add_parser("timeline"); tl.add_argument("path"); tl.add_argument("registry", nargs="?"); tl.set_defaults(func=cmd_timeline)
    a = p.parse_args(); a.func(a)


if __name__ == "__main__":
    main()
