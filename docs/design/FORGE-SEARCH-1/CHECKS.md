# Design checks

The checks ran on the four artboards in `src/` and their 1440 by 900 images. The fixes went into
the artboards in one pass, and the images were made again with `.forge/design/support.js`.

## Critique

Method: impeccable critique, single context (this design ran as one agent), with the impeccable
detector on `src/`.

- The panel was centred on the screen, so it would move up and down as the groups came and went
  with each keystroke. Fixed: the panel has a fixed top position, 80px from the top.
- The hint under the short query said `letters`, but numbers also count. Fixed: it says
  `characters`.
- The single-line entries (pages and actions) had no space above and below the text. Fixed: they
  have 10px, as in the shadcn command item.
- Detector: the `Ctrl K`, `Enter` and `Esc` hints had 4.3 to 1 contrast, muted text on the muted
  fill. Fixed: the hint text uses the foreground colour on the muted fill.
- Detector: the status under the selected result had 4.3 to 1 contrast on the accent fill.
  Fixed: the selected row's status uses the accent foreground colour.
- Detector: the states artboard's grey canvas lowered the contrast of the muted text. Fixed: the
  canvas is the page background.
- Detector, not changed: "cramped padding" on the top-bar search box, the table wrapper and the
  panel footer. The search box and the footer centre one line of text in 36px and 40px, and the
  table cells have the shadcn 8px padding, so these are false positives.

Result: passed

## Polish

- Every control has a name for screen readers: the top-bar box (`Search the app`), the panel's
  search field, the chips (buttons with `aria-pressed`, in a group named `Search in`), and each
  result (an option in the listbox, with its group's name).
- The panel's search field is a combobox that controls the results listbox; the selected entry
  has `aria-selected`. Loading has a status (`Searching…`), no results has a status, and the
  error is an alert.
- The keyboard path: Ctrl K or typing opens the panel with the focus in its field; ↑ ↓ move,
  Enter opens, Esc closes and returns the focus to the top-bar box; Tab reaches the chips.
- Spacing, radius, borders, type sizes and colours are the starter's shadcn tokens, as on the
  FORGE-FEATURE-1 artboards. No new token.
- Loading, no-results, error and short-query states and their copy are in SCREENS.md, with the
  permission rules for results, chips, pages and actions.

Result: passed

## Emil checklist

- No new animation. The panel uses the shadcn Dialog's open and close, which animate only
  transform and opacity and stay under 300ms.
- The results, the selection and the chips change with no animation, because people use the
  panel many times a day from the keyboard.
- The panel keeps a fixed top position, and the old results stay until the new ones arrive, so
  nothing jumps while the person types.
- The skeleton shows only after 150 ms of waiting and only when no results are on screen yet,
  so a fast search does not flash.
- The selected row is a background colour only, with no movement.

Result: passed
