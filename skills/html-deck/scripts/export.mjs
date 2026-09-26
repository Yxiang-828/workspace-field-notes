// export.mjs — render every slide to a zero-loss PNG at exact slide dimensions.
//   node scripts/export.mjs <deckDir> [--scale 2] [--only 03]
// Output: <deckDir>/build/export/<slide-id>.png  (PNG = lossless; 1280x720 * scale)
// Drives headless Chrome via puppeteer-core (no Chromium download).
// NOTE: run with the Bash sandbox DISABLED — Google Fonts are fetched over the network.
import puppeteer from 'puppeteer-core';
import { readdirSync, statSync, existsSync, mkdirSync, unlinkSync } from 'node:fs';
import { join, resolve, basename } from 'node:path';
import { pathToFileURL } from 'node:url';

const W = 1280, H = 720;
const args = process.argv.slice(2);
const deckDir = resolve(args[0] || '.');
const scale = Number((args[args.indexOf('--scale') + 1]) || 2) || 2;
const only = args.includes('--only') ? args[args.indexOf('--only') + 1] : null;

function findChrome() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;
  const c = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ];
  for (const p of c) if (existsSync(p)) return p;
  throw new Error('No Chrome/Edge found; set CHROME_PATH');
}

const slidesDir = join(deckDir, 'slides');
if (!existsSync(slidesDir)) throw new Error('No slides/ dir in ' + deckDir);
const outDir = join(deckDir, 'build', 'export');
mkdirSync(outDir, { recursive: true });
// full export clears stale PNGs (e.g. from renamed/removed slides); --only keeps them
if (!only) for (const f of readdirSync(outDir)) if (f.endsWith('.png')) unlinkSync(join(outDir, f));

let slides = readdirSync(slidesDir)
  .filter(d => statSync(join(slidesDir, d)).isDirectory())
  .filter(d => existsSync(join(slidesDir, d, 'slide.html')))
  .sort();
if (only) slides = slides.filter(s => s.includes(only));
if (!slides.length) throw new Error('No slides found');

const browser = await puppeteer.launch({
  executablePath: findChrome(),
  headless: 'new',
  args: ['--no-sandbox', '--hide-scrollbars', '--disable-gpu'],
});
try {
  for (const s of slides) {
    const page = await browser.newPage();
    await page.setViewport({ width: W, height: H, deviceScaleFactor: scale });
    const url = pathToFileURL(join(slidesDir, s, 'slide.html')).href;
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
    await page.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    const out = join(outDir, s + '.png');
    await page.screenshot({ path: out, clip: { x: 0, y: 0, width: W, height: H } });
    console.log(`  ✓ ${basename(out)}  (${W * scale}x${H * scale})`);
    await page.close();
  }
} finally {
  await browser.close();
}
console.log(`\nExported ${slides.length} slide(s) -> ${outDir}`);
