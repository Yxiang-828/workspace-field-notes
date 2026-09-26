# Dock panelling for modular consoles — verified verdict (2026-07-20)

When a product's growth model is "capabilities are panels" (dockable,
resizable, floatable, persisted), use **dockview** — pinned, currently 7.0.2.
First verified use: keel-2 `shipyard/` (live-driven, motion checker clean).

## Why dockview (over the field)

- Panel registry is its native model: `components={{name: Component}}` — a
  string-keyed map; names serialize into layout JSON. A new capability is one
  registry entry; the shell never changes.
- Theming is CSS-custom-properties-first (`--dv-*`). Layer your tokens over a
  shipped base theme class so unmapped vars inherit sane defaults:
  `className: "dockview-theme-dark your-theme"`.
- Full feature set: tabs, splits, floating groups, popout windows, maximize;
  serialize/restore is `api.toJSON()` / `api.fromJSON()` + `onDidLayoutChange`.
- Healthiest maintenance in the category (weekly releases mid-2026, a11y module
  shipped v7.0.2, MIT, zero-dep core, ~75 KB gzip, React 16.8–19).
- Fallback if dockview ever dies: **flexlayout-react**. Do not reach for
  golden-layout (abandoned 2022), rc-dock (alpha limbo), react-mosaic (no
  float/popout), Lumino (fights React), or hand-rolling (months of table
  stakes).

## Sharp edges (hit or verified in the field)

- Import from **`dockview-react`** (v7 split `dockview` into the vanilla pkg);
  pre-2026 tutorials show the old import. Pin the version — majors land fast.
- `fromJSON` throws on unknown component names → always try/catch and fall
  back to a default layout; never rename a registry key without migrating
  stored JSON.
- Default renderer destroys hidden-panel DOM. Log/terminal panels need
  `renderer: "always"` or scrollback dies on tab switch.
- **Never scale the app with CSS `zoom`** (verified-live, keel-2 shipyard
  2026-07-20): zoom desyncs dockview's measured px from visual px, so
  `renderer:"always"` panels draw ~scale-factor past their split, overlapping
  neighbor groups. Bake the comfort scale into the px values (or rem)
  instead — real pixels, nothing to mismeasure.
- **A dockview panel has NO minimum height** (verified-live, keel-2 shipyard
  2026-07-21): a split can hand your panel 320px while its fixed chrome wants
  590px. Never `overflow: hidden` a panel that stacks fixed chrome around an
  inner scroller — below-the-fold controls become invisible AND unreachable
  (users report "UI only appears when I zoom out"). Use `overflow: hidden auto`
  on the panel: when there's room the flex:1 inner list absorbs the slack and
  stays the only scroller; in a short split the panel itself degrades to
  scrolling. Verify at the real deploy viewport (1280×800), not a roomy one.
- Popouts need a blank same-origin `popout.html` (Vite: in `public/`); runtime-
  injected styles don't copy into popouts — keep tokens in real stylesheets.
- Floating/popout groups cannot be maximized (documented no-op).

## Proven wiring pattern

```tsx
const components = { berth: Berth, logs: Logs /* registry-built */ };
const onReady = (e: DockviewReadyEvent) => {
  const saved = localStorage.getItem(KEY);
  try { saved ? e.api.fromJSON(JSON.parse(saved)) : defaultLayout(e.api); }
  catch { localStorage.removeItem(KEY); defaultLayout(e.api); }
  e.api.onDidLayoutChange(debounce(() =>
    localStorage.setItem(KEY, JSON.stringify(e.api.toJSON())), 250));
};
<DockviewReact theme={{ name: "x", className: "dockview-theme-dark x-theme",
  colorScheme: "dark" }} components={components} onReady={onReady} />
```

State for panels: a module store + `useSyncExternalStore`, not React context —
panels can move into popout windows and a store keeps every surface on the
same truth. Panels the server declares (a `panels.json` registry endpoint)
beat panels hardcoded client-side: growth stays data-driven.
