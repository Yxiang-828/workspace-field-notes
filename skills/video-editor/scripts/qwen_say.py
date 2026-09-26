#!/usr/bin/env python3
"""Qwen3-TTS voice-clone narration via the baked docker image, with the FULL external
voice library mounted in (so all 21 ref voices work, not just the 8 baked).
usage: py qwen_say.py --voice 15_soothing_woman --text "..." --out path.wav
"""
import argparse, os, subprocess, sys

VOICES = os.environ.get('QWEN_VOICE_DIR', os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'assets', 'voice_actors', 'english')))
IMG = 'qwen-tts:baked'

def synth(text, voice, out, seed=281):
    outdir = os.path.dirname(os.path.abspath(out))
    name = os.path.splitext(os.path.basename(out))[0]
    os.makedirs(outdir, exist_ok=True)
    cmd = ['docker', 'run', '--rm', '-i',
           '-v', f"{outdir.replace(chr(92),'/')}:/out",
           '-v', f"{VOICES.replace(chr(92),'/')}:/bundle/voice_actors/english:ro",
           IMG,
           '--model', '/bundle/models/qwen-talker-0.6b-base-Q4_K_M.gguf',
           '--codec', '/bundle/models/qwen-tokenizer-12hz-Q4_K_M.gguf',
           '--lang', 'english',
           '--ref-wav', f'/bundle/voice_actors/english/{voice}.wav',
           '--ref-text', f'/bundle/voice_actors/english/{voice}.txt',
           '--seed', str(seed), '--format', 'wav16', '-o', f'/out/{name}.wav']
    r = subprocess.run(cmd, input=text.encode('utf-8'), stderr=subprocess.PIPE)
    if r.returncode != 0 or not os.path.exists(out):
        print("FAIL:", r.stderr.decode(errors='replace')[-400:], file=sys.stderr)
        return None
    print(f"ok: {out} ({os.path.getsize(out)} bytes)")
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--voice', default='15_soothing_woman')
    ap.add_argument('--text', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=281)
    a = ap.parse_args()
    synth(a.text, a.voice, a.out, a.seed)
