# Component integration

Use this checklist for a 21st.dev or other supplied React component.

1. Confirm the exact source snippet and its package imports. Do not guess missing dependencies.
2. Identify the component's actual job in the product; remove demo-only copy and decoration.
3. Replace colors, radii, shadows, type, spacing, and icons with local tokens.
4. Preserve semantics, labels, focus order, keyboard operation, and visible focus.
5. Replace blanket animation with entries from the product motion map.
6. Test empty, loading, long-copy, error, narrow-window, reduced-motion, forced-colors, and 125–200% Windows scaling states when relevant.
7. Confirm accessible names, non-color status cues, live announcements for asynchronous results, modal focus trap/return, and a single-click or keyboard alternative to any double-click shortcut.
8. Keep attribution or license material required by the supplied source.
9. Render it beside adjacent local components and fix any obvious visual seam.
