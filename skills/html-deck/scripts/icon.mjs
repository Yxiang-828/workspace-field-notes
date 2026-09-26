// icon.mjs — list bundled icons / fetch a brand logo on demand.
//   node scripts/icon.mjs list [ui|logos]
//   node scripts/icon.mjs fetch <slug> [destDir]    (network; run sandbox OFF)
// Brand logos come from Simple Icons (3000+); slug = the simpleicons.org name.
import { readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = dirname(fileURLToPath(import.meta.url));
const ASSETS = join(__dir, '..', 'assets');
const [cmd, a, b] = process.argv.slice(2);

if (cmd === 'list') {
  const which = a === 'logos' ? 'logos' : 'icons';
  const names = readdirSync(join(ASSETS, which)).filter(f => f.endsWith('.svg')).map(f => f.replace('.svg', '')).sort();
  console.log(`${names.length} ${which}:`);
  console.log(names.join('  '));
} else if (cmd === 'fetch') {
  if (!a) { console.error('usage: icon.mjs fetch <slug> [destDir]'); process.exit(1); }
  const dest = b ? resolve(b) : join(ASSETS, 'logos');
  mkdirSync(dest, { recursive: true });
  const urls = [`https://cdn.simpleicons.org/${a}`, `https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/${a}.svg`];
  let svg = null;
  for (const u of urls) {
    try { const r = await fetch(u); if (r.ok) { const t = await r.text(); if (t.includes('<svg')) { svg = t; break; } } } catch {}
  }
  if (!svg) { console.error(`not found: "${a}" — check the slug at simpleicons.org`); process.exit(2); }
  const out = join(dest, `${a}.svg`);
  writeFileSync(out, svg);
  console.log(out);
} else {
  console.log('usage: icon.mjs {list [ui|logos] | fetch <slug> [destDir]}');
}
