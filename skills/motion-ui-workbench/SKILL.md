---
name: motion-ui-workbench
description: Design, build, present, and verify distinctive digital products through coherent interface systems, purposeful Motion/Framer Motion animation, native-desktop polish, product screenshots and imagery, and composed README/Markdown surfaces. Use for Windows/web app frontends, dashboards, landing pages, onboarding, animated covers, 21st.dev-style component adaptation, repository presentation, release pages, screenshot direction, or any request for premium product-facing visual craft.
---

# Motion UI Workbench

Build and present the product as one product-specific visual system, then use motion only where it explains, connects, or confirms state. Frontend craft includes native windows, screenshots, release imagery, and README composition as well as the rendered interface. Treat the supplied `frontend.txt` stack as a starting point, not a command to animate every element.

## Workflow

1. Ground the design in one subject, one audience, and one primary job. Read the available `frontend-design` and `emil-design-eng` skills when present. Name the product surface being designed: live interface, native shell, repository/README, release page, screenshot set, or a coordinated combination.
2. Plan before coding:
   - define 4–6 named color tokens;
   - assign distinct display, body, and utility type roles;
   - sketch two compact layout options;
   - choose one memorable, subject-derived signature element;
   - critique and replace anything that could belong to an unrelated app.
3. Write a motion map for each proposed animation. Use this shape and delete rows that do not earn their place:

   | Moment | Frequency | Purpose | Technique | Duration | Reduced motion |
   | --- | --- | --- | --- | --- | --- |
   | Example drawer | Occasional | Preserve spatial context | Presence + nearby transform | 180 ms in / 130 ms out | Opacity only |

   Frequent keyboard state changes must respond immediately; a surrounding transition is acceptable only when it neither delays input nor obscures the new focus/state. Keep ordinary UI feedback below 300 ms.
4. Build with React and the current Motion package (`motion/react`) for new projects. Preserve `framer-motion` imports in an established project unless migration is part of the request.
5. Prefer CSS transitions for predetermined transform/opacity effects. Use Motion for interruptible gestures, shared layout, presence, or scroll-linked state. Never use animation to delay interaction.
6. Integrate external components as raw material: map them to the local tokens, copy, focus behavior, responsive rules, and motion language. Do not leave a pasted component visually or behaviorally foreign.
7. Use generated frames only when the signature moment cannot be expressed cleanly with HTML/CSS/SVG. Follow [frame-handoff.md](references/frame-handoff.md) and give the user one exact generation prompt before requesting assets.
8. Verify with keyboard navigation, reduced motion, narrow and wide layouts, 125–200% Windows scaling when relevant, forced colors, empty/loading/error states, long content, and rendered screenshots. Run the checker by resolving it from this skill's directory, not the project directory:

   ```powershell
   node <motion-ui-workbench-skill-root>\scripts\check_motion_ui.mjs <project-directory>
   ```

9. Review the result after rendering. Remove one decorative element, shorten one slow interaction, and fix the most obvious hierarchy or spacing weakness before handoff.

## Repository and product presentation

- Treat a README as a product surface, not a text dump. Establish a visual opening, one decisive product statement, an obvious action, a proof screenshot, then the operating detail. Use GitHub-flavored Markdown and restrained HTML alignment deliberately.
- Direct screenshots like product photography: choose the state, viewport, crop, demo content, and surrounding negative space before capture. Use sanitized representative data and a real rendered build. Never publish personal paths, credentials, private project names, or accidental desktop chrome.
- Prefer code-native SVG for brand geometry, diagrams, and reusable interface motifs. Use bitmap generation or sourced imagery only when texture, illustration, place, people, or atmosphere materially improves understanding.
- Keep badges subordinate. Do not let a wall of badges, tables, or screenshots replace hierarchy and narrative.
- For desktop products, include shell quality in the visual system: installer art, application icon, Start/Search name, title bar, Windows scaling, high contrast, and screenshot behavior at the user's actual scale.
- Verify repository-relative asset paths, alt text, light/dark GitHub backgrounds, narrow rendering, release links, and that every depicted state still matches the shipped build.

## Interaction rules

- Give primary pressable controls an immediate active response around `scale(0.97)` when motion helps. Prefer a color, border, or contrast response for compact menu items, toggles, dense repeated controls, and reduced-motion users.
- Use strong ease-out for entrances and faster exits; do not use `ease-in` for UI responses.
- Animate from a visible nearby state, such as `scale(0.95)` plus opacity, never `scale(0)`.
- Animate transform and opacity where possible. Avoid `transition: all`.
- Set popover transform origins at their triggers; keep modal origins centered.
- Gate hover-only effects with `(hover: hover) and (pointer: fine)`.
- Reserve orchestrated or scroll-linked sequences for rare moments such as a first-run cover or product explanation.
- Provide a non-moving equivalent under `prefers-reduced-motion` or Motion's `useReducedMotion`.
- Give every control an accessible name. Trap and restore focus for modal dialogs, announce asynchronous outcomes through a live region, and never use color as the only status signal.
- Test forced-colors/high-contrast behavior. Use incremental rendering or virtualization when a long repeated list becomes measurably slow.

## Component intake

When using a 21st.dev or other third-party block, ask for or use the exact component code already supplied in scope. Inspect its dependencies and behavior, then adapt it instead of reproducing its demo styling. Read [component-integration.md](references/component-integration.md) for the intake checklist.

## Frame-to-motion collaboration

Treat the user as a frame-generation API only when frames materially improve the design. Specify aspect ratio, pixel size, frame count, camera lock, unchanged elements, exact per-frame deltas, background/alpha, naming, and negative constraints. Do not ask for vague “cool frames.” Once supplied, preload the sequence, bind it to one deliberate cover/scroll interaction, and make the reduced-motion state a useful still frame.
