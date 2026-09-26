# Deck content playbook + guardrails (read before building any deck)

Layout/CSS is solved by the engine. This file governs **what goes on each slide** and **what you are not allowed to make up**. Good decks are read in ~2.5 minutes (DocSend): one idea per slide, show > tell, 10–15 slides max.

## 1. Pick the deck type first

- **Investor / pitch deck** (raising, selling a venture) → Sequoia order below.
- **Product / demo deck** (showing how a built thing works) → Problem → Solution → How it works → Product/Demo → Tech → What's next.
- **Project showcase** (portfolio, hackathon, case study) → What it is (1 line) → Problem → Approach → How it works → Result/Demo → Stack → Reflection. *Use this for portfolio projects; do NOT bolt on investor slides (Market/Traction/Ask) that don't apply.*

## 2. Sequoia 10-slide order (the investor default)

1. **Purpose** — one sentence: what the company does.
2. **Problem** — the pain, made concrete; who feels it.
3. **Solution** — how you solve it; the "aha".
4. **Why now** — the shift that makes this possible/urgent.
5. **Market size** — who and how many; bottom-up if possible.
6. **Competition** — the landscape + your wedge.
7. **Product** — show it. Screens, demo, the thing working.
8. **Business model** — how money is made.
9. **Traction** — proof: usage, growth, revenue, pilots.
10. **Team** — why you. Then **The Ask** — amount + use of funds.

Investors evaluate risk in this order (believe the problem → understand the solution → market worth it → can they execute). Don't reorder without reason; don't pad.

## 3. ANTI-BS GUARDRAILS (hard rules — this is why this file exists)

**Ground every claim in the source material. Pitch only what exists.**

- **Never invent**: traction numbers, user counts, revenue, growth %, market-size figures, funding, customers, partnerships, awards, team members, or quotes. If it's not in the source (project files / what the user told you), it does not go on a slide.
- **No placeholder metrics as if real.** A stat slide with `10×` / `98%` from the template is a PROMPT to you, not content — replace with a real figure or **cut the slide**. Never ship invented numbers.
- **Missing standard slide → omit or reframe, don't fabricate.** No real traction? Drop the Traction slide (or show a qualitative "status: prototype / hackathon build"). No market data? Drop Market or state the segment qualitatively. Honesty reads as competence.
- **Separate fact from framing.** You may sharpen language and structure; you may not assert capabilities the thing doesn't have. "Searches marketplaces in parallel" (in source) ✓. "Used by 10k shoppers" (not in source) ✗.
- **Assets you don't have → descriptive placeholder, not a fake.** Use a zone with `data-desc` saying exactly what real screenshot/diagram belongs there. Never generate a fake screenshot and present it as the real product.
- **Numbers/claims you keep must be traceable** to a source line. If unsure, leave it out or ask.

## 4. Build process (do this every time)

1. **Extract** the source into a fact list (what it is, problem, how it works, stack, status, real numbers if any). Quote/locate each.
2. **Choose** deck type + slide list. Drop any slide with no real content.
3. **Outline** one headline + one visual intent per slide (≤15). Mark each visual with a `data-desc` describing the asset.
4. **Build** slides from the fact list only. Then re-read every claim and confirm it traces to the source. Cut anything that doesn't.
5. Export PNGs; host via here-now if asked.
