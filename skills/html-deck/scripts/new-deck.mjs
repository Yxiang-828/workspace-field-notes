// new-deck.mjs — scaffold an adaptable, visual-first HTML deck.
//   node scripts/new-deck.mjs <deckDir> "Deck Title" [--theme midnight|ocean|amber|mono|light]
// Copies the icon/logo asset library + chosen theme into the deck so it is
// self-contained (hostable). Starter slides are visual-first with descriptive
// placeholders (they say WHAT image to show, not just a filename).
import { mkdirSync, writeFileSync, copyFileSync, cpSync, existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = dirname(fileURLToPath(import.meta.url));
const SKILL = join(__dir, '..');

const argv = process.argv.slice(2);
const flagIdx = argv.indexOf('--theme');
const theme = flagIdx >= 0 ? argv[flagIdx + 1] : 'midnight';
const positional = argv.filter((v, i) => v !== '--theme' && argv[i - 1] !== '--theme');
const deckDir = resolve(positional[0] || './deck');
const title = positional[1] || 'Untitled Deck';
if (existsSync(join(deckDir, 'deck.json'))) { console.error('Deck already exists:', deckDir); process.exit(1); }

const slidePage = (id, inner, bodyClass = '') =>
`<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<link rel="stylesheet" href="../../deck.css"><link rel="stylesheet" href="../../theme.css">
<title>${id}</title></head>
<body><section class="slide ${bodyClass}">
${inner}
</section></body></html>`;

// Visual-first starter slides. Each demonstrates a pattern; replace the content.
const slides = [
  // 01 — full-bleed hero image with overlaid title (image is the slide)
  ['01-title', slidePage('01-title', `  <figure class="zone fill" data-label="media/cover.png" data-desc="The single most striking visual for this deck — a hero render, product shot, or bold cover image. Full-bleed.">
    <img src="media/cover.png" alt="" onerror="this.remove()">
  </figure>
  <div class="overlay">
    <div class="eyebrow">DECK · 2026</div>
    <h1 class="title">${title.replace(/&/g,'&amp;')} <em>—</em></h1>
    <p class="sub">One-line thesis. Replace this. Lead with the image; keep words few.</p>
  </div>
  <div class="brandline">YAO XIANG</div><div class="slide-no">01</div>`, 'image-hero')],

  // 02 — feature: slim icon-bullet column + BIG image
  ['02-feature', slidePage('02-feature', `  <div class="feature">
    <div class="col">
      <div class="eyebrow">WHAT IT IS</div>
      <h2 class="title">One idea, <em>shown.</em></h2>
      <ul class="bullets" style="margin-top:8px">
        <li><b>Point one</b> — kept to a single line.</li>
        <li style="--bullet:url(../../assets/icons/zap.svg)"><b>Point two</b> — icon carries the meaning.</li>
        <li style="--bullet:url(../../assets/icons/trending-up.svg)"><b>Point three</b> — the result.</li>
      </ul>
    </div>
    <figure class="zone r-16x9" data-label="media/screen.png" data-desc="The product in action — a large, clean screenshot or demo frame of the main UI. This should dominate the slide.">
      <img src="media/screen.png" alt="" onerror="this.remove()">
    </figure>
  </div>
  <div class="slide-no">02</div>`)],

  // 03 — tech stack / brand logos
  ['03-stack', slidePage('03-stack', `  <div class="eyebrow">BUILT WITH</div>
  <h2 class="title">The <em>stack.</em></h2>
  <div class="spacer"></div>
  <div class="logo-row mono">
    <img class="logo" src="../../assets/logos/openai.svg" alt="OpenAI">
    <img class="logo" src="../../assets/logos/python.svg" alt="Python">
    <img class="logo" src="../../assets/logos/react.svg" alt="React">
    <img class="logo" src="../../assets/logos/nodedotjs.svg" alt="Node">
    <img class="logo" src="../../assets/logos/docker.svg" alt="Docker">
    <img class="logo" src="../../assets/logos/huggingface.svg" alt="Hugging Face">
  </div>
  <p class="sub" style="margin-top:32px">Swap logos from <code>assets/logos/</code>; fetch any brand with <code>icon.mjs fetch &lt;slug&gt;</code>. Add <code>.mono</code> for uniform white on dark.</p>
  <div class="spacer"></div>
  <div class="slide-no">03</div>`)],

  // 04 — big numbers + icon cards
  ['04-stats', slidePage('04-stats', `  <div class="eyebrow">TRACTION</div>
  <h2 class="title">The <em>numbers.</em></h2>
  <div class="spacer"></div>
  <div class="stats">
    <div class="stat"><div class="v">10×</div><div class="l">metric one</div></div>
    <div class="stat"><div class="v">2.4s</div><div class="l">metric two</div></div>
    <div class="stat"><div class="v">98%</div><div class="l">metric three</div></div>
    <div class="stat"><div class="v">29</div><div class="l">metric four</div></div>
  </div>
  <div class="spacer"></div>
  <div class="cards c3">
    <div class="card"><i class="card-ic" style="--svg:url(../../assets/icons/zap.svg)"></i><h3>Fast</h3><p>One supporting line.</p></div>
    <div class="card"><i class="card-ic" style="--svg:url(../../assets/icons/shield.svg)"></i><h3>Solid</h3><p>One supporting line.</p></div>
    <div class="card"><i class="card-ic" style="--svg:url(../../assets/icons/users.svg)"></i><h3>Loved</h3><p>One supporting line.</p></div>
  </div>
  <div class="slide-no">04</div>`)],

  // 05 — edge-to-edge single visual with caption bar
  ['05-bigmedia', slidePage('05-bigmedia', `  <figure class="zone fill" data-label="media/diagram.png" data-desc="One big explanatory visual — architecture diagram, full dashboard, or before/after. Edge to edge. Let it breathe.">
    <img src="media/diagram.png" alt="" onerror="this.remove()">
  </figure>
  <div class="capbar"><span class="kicker">HOW IT WORKS</span><span class="sub" style="margin:0">A one-line caption under the visual.</span></div>
  <div class="slide-no">05</div>`, 'tight')],

  // 06 — closing line
  ['06-close', slidePage('06-close', `  <blockquote class="quote">&ldquo;The closing line that they remember.&rdquo;<span class="by">— the ask / next step</span></blockquote>
  <div class="slide-no">06</div>`, 'bg-aurora center')],
];

mkdirSync(deckDir, { recursive: true });
copyFileSync(join(SKILL, 'deck.css'), join(deckDir, 'deck.css'));
// theme
const themeSrc = join(SKILL, 'assets', 'themes', `${theme}.css`);
copyFileSync(existsSync(themeSrc) ? themeSrc : join(SKILL, 'assets', 'themes', 'midnight.css'), join(deckDir, 'theme.css'));
// self-contained asset library (icons + logos) — slides reference ../../assets/...
cpSync(join(SKILL, 'assets', 'icons'), join(deckDir, 'assets', 'icons'), { recursive: true });
cpSync(join(SKILL, 'assets', 'logos'), join(deckDir, 'assets', 'logos'), { recursive: true });

const ids = [];
for (const [id, html] of slides) {
  const dir = join(deckDir, 'slides', id);
  mkdirSync(join(dir, 'media'), { recursive: true });
  writeFileSync(join(dir, 'slide.html'), html);
  writeFileSync(join(dir, 'media', '.keep'), '');
  ids.push(id);
}

const frames = ids.map(id => `  <section class="page"><iframe src="slides/${id}/slide.html" scrolling="no"></iframe></section>`).join('\n');
writeFileSync(join(deckDir, 'index.html'),
`<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>${title}</title>
<style>
  html,body{margin:0;background:#000;} html{scroll-snap-type:y mandatory;}
  .page{height:100vh;display:grid;place-items:center;scroll-snap-align:start;}
  iframe{width:1280px;height:720px;border:0;transform:scale(min(calc(100vw/1280),calc(100vh/720)));}
</style></head><body>
${frames}
</body></html>`);

writeFileSync(join(deckDir, 'deck.json'),
  JSON.stringify({ title, theme, canvas: { w: 1280, h: 720, ratio: '16:9' }, exportScale: 2, slides: ids }, null, 2));

writeFileSync(join(deckDir, 'README.md'),
`# ${title}

Visual-first HTML deck. Canvas **1280×720 (16:9)** → export **2560×1440 lossless PNG** (zero-crop in Google Slides). Theme: \`${theme}\`.

## Principles
Show the thing, not walls of text. One idea per slide. **10–15 slides max.** Every visual slide has a zone with a \`data-desc\` describing *what* image to drop in.

## Media (fixed convention)
Per-slide assets: \`slides/<id>/media/\` → reference as \`media/<file>\`. Shared assets (icons/logos): \`assets/…\` → reference as \`../../assets/icons/<name>.svg\` or \`../../assets/logos/<slug>.svg\`.

## Commands
\`\`\`bash
node <skill>/scripts/export.mjs "${'$'}PWD"            # PNGs -> build/export  (sandbox OFF)
node <skill>/scripts/icon.mjs list logos              # bundled brand logos
node <skill>/scripts/icon.mjs fetch <slug> assets/logos   # fetch any brand (sandbox OFF)
\`\`\`
Host live (with video) by publishing this folder via the here-now skill (\`index.html\`).
`);

console.log(`Deck scaffolded at ${deckDir}  (theme: ${theme})`);
console.log('Slides:', ids.join(', '));
