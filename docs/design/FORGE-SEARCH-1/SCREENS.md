# Screens for one search across the whole app

Structure only. Every screen uses the starter's neutral shadcn/ui theme and its existing app shell
(sidebar, header, user menu). No new look, colour or font. The panel is the starter's existing
Ctrl+K `CommandDialog`, with chips and record results added.

The example app has three modules: Projects, Invoices and Clients. Each module's sidebar link
comes from `forge task feature`, as on the FORGE-FEATURE-1 screens. A module's search uses its
name field (the first text field) for the title and its first status-list field for the
subtitle.

Permissions, on every screen:

- A result the person cannot view is never shown.
- A module the person cannot view has no chip and no group.
- Pages and actions follow the sidebar's rules: `Change history` and `Invite person` show only
  for admins.

## Top bar search

Image: top-bar-search.png
Route: every page inside the app shell; the image shows `/projects`.
Components: Input, kbd hint (in the header, next to the user menu)
Fields:
- Search: text, optional

- The header's `Search` button becomes a search box, 256px wide: a search icon, the placeholder
  `Search…` and the hint `Ctrl K` on the right. On a Mac the hint is `⌘ K`.
- Screen-reader label: `Search the app`.
- A click in the box, or `Ctrl K` / `⌘ K` anywhere, opens the search panel. Typing in the box
  opens the panel with the typed text in the panel's search field, and the focus moves there.
- On a phone the box becomes the icon button the starter has now (label `Search`), and a tap
  opens the panel.

## Search panel

Image: search-panel.png
Opens from the top bar on a page that is not a module's page; the image shows it over
`/members` with `pro` typed.
Components: CommandDialog, CommandInput, CommandList, CommandGroup, CommandItem, Button (chips,
small, `aria-pressed`)
Fields:
- Search: text, optional
- Search in: choice, required, options: All | each module the person can view (here Projects |
  Invoices | Clients), default All

- Panel title for screen readers `Search`, description `Search pages, actions and records.`
  Search field placeholder `Search…`, label `Search pages, actions and records`.
- Chips under the search field: `All`, then one chip per module in sidebar order. The chosen chip
  has the secondary fill and a border. The chips are buttons; Tab reaches them from the search
  field.
- With `All`, the list shows, in this order:
  1. `Pages and actions`: the pages and actions whose names match, for example `Projects` and
     `New project`. These come from the app, with no search call.
  2. One group per module, headed with the module's name, with up to five results each. A result
     has the module's icon, the title (`Product launch`) and the status under it (`Active`).
     A module with no results has no group.
- The first entry is selected when the results change. ↑ and ↓ move the selection, Enter opens
  it, Esc closes the panel. A record opens its detail screen; a page opens the page; an action
  runs (for example `New project` opens the project form).
- The search starts at two characters and runs 150 ms after the person stops typing. Results are
  ranked by how well the title matches.
- The list scrolls when it is taller than 640px (60% of the window height on a small screen).
  The panel stays at the same top position, so it does not move as results come and go.
- Footer hint: `↑ ↓ to move`, `Enter to open`, `Esc to close`. It is hidden from screen readers;
  the listbox roles give the same keys.
- On a phone the panel fills the width with a 16px gutter and the chips scroll sideways.

## Search panel on a module's page

Image: search-panel-module.png
Opens from the top bar on a module's list or detail page; the image shows it over `/projects`
with `pro` typed.
Components: as Search panel
Fields: as Search panel, with Search in defaulting to the page's module

- The module's chip (`Projects`) is already chosen.
- With a module chip, the list shows only that module's results, up to 20, in one group with the
  module's name. Pages and actions do not show. The list scrolls past 640px.
- `All` brings back pages, actions and every module's group. The chosen chip is not kept between
  openings: each opening starts on the page's module.

## Search states

Image: search-states.png
The four panel states, shown side by side.
Components: CommandDialog, CommandGroup, CommandItem, CommandEmpty, Skeleton
Fields: as Search panel

- **Fewer than two characters** (and when the panel opens empty): only `Pages and actions`,
  filtered by the text typed, with no search call. Under it, in muted text: `Type two or more
  characters to search projects, invoices and clients.` The sentence names only the modules the
  person can view.
- **No results**: `No results for “xyz”.` (status), centred. This shows only when no page,
  action or record matches.
- **Loading**: the matching pages and actions show at once. In place of the module groups, three
  quiet skeleton rows (an icon square, a title bar and a status bar, in the shadcn Skeleton fill),
  with `Searching…` for screen readers. The skeleton shows only if the search takes more than
  150 ms after it starts; a fast search goes straight to results. The skeleton shows only when
  there are no results on screen yet; once there are, they stay until the new results arrive.
- **Error**: `Search is not available. Try again.` (alert) with the alert icon, in place of the
  module groups. Pages and actions still show. The next change to the text tries again.
