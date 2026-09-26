// make-cards.mjs — render full-screen section-marker cards (html-deck aesthetic) to PNG.
//   node make-cards.mjs cards.json     where cards.json = [{ "title":"…", "file":"…png" }, …]
// 1920x1080, transparent-free dark card. Uses headless Chrome via puppeteer-core (from html-deck).
// Run with the Bash sandbox DISABLED (Google Fonts load over the network).
import puppeteer from "puppeteer-core";
import { readFileSync, existsSync } from "node:fs";

const cards = JSON.parse(readFileSync(process.argv[2], "utf8"));
const CHROME = ["C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(existsSync);

const html = (title, idx, n) => `<!DOCTYPE html><html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;500&family=Fraunces:ital,opsz,wght@0,9..144,900;1,9..144,400&display=swap" rel="stylesheet">
<style>
  *{margin:0;box-sizing:border-box} html,body{width:1920px;height:1080px}
  body{background:#07050c;color:#ece4ff;font-family:'DM Mono',monospace;display:flex;flex-direction:column;justify-content:center;padding:0 160px;position:relative;overflow:hidden}
  body::after{content:'';position:absolute;inset:-25%;z-index:0;filter:blur(110px);
    background:radial-gradient(closest-side at 22% 32%,rgba(217,111,255,.20),transparent 60%),
               radial-gradient(closest-side at 80% 24%,rgba(95,217,255,.16),transparent 65%),
               radial-gradient(closest-side at 62% 82%,rgba(255,111,184,.18),transparent 60%)}
  .grid{position:absolute;inset:0;z-index:0;background-image:linear-gradient(rgba(217,111,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(95,217,255,.05) 1px,transparent 1px);background-size:80px 80px}
  .wrap{position:relative;z-index:1}
  .eyebrow{font-family:'Bebas Neue',sans-serif;letter-spacing:10px;font-size:30px;color:#5fd9ff;text-transform:uppercase;display:flex;align-items:center;gap:24px;margin-bottom:30px}
  .eyebrow::before{content:'';width:70px;height:2px;background:#5fd9ff}
  .num{position:absolute;top:60px;right:160px;z-index:1;font-family:'Bebas Neue',sans-serif;font-size:34px;letter-spacing:4px;color:rgba(217,111,255,.5)}
  h1{font-family:'Fraunces',serif;font-weight:900;font-size:150px;line-height:.94;letter-spacing:-4px}
  h1 em{font-style:italic;background:linear-gradient(120deg,#d96fff,#ff6fb8 55%,#5fd9ff);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
</style></head><body>
  <div class="grid"></div>
  <div class="num">${String(idx).padStart(2,"0")} / ${String(n).padStart(2,"0")}</div>
  <div class="wrap"><div class="eyebrow">Section</div><h1><em>${title}</em></h1></div>
</body></html>`;

const b = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
try {
  for (let i = 0; i < cards.length; i++) {
    const p = await b.newPage();
    await p.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
    await p.setContent(html(cards[i].title, i + 1, cards.length), { waitUntil: "networkidle0", timeout: 30000 });
    await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    await p.screenshot({ path: cards[i].file });
    await p.close();
    console.log("card:", cards[i].file);
  }
} finally { await b.close(); }
