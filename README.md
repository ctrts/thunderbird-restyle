# Thunderbird Restyle

A modern, floating-pane theme for Thunderbird 155 on Omarchy.

The window chrome — spaces bar, tab bar, toolbar — is a recessed gutter, and
the folder pane, message list and reading pane sit on it as rounded, softly
shadowed surfaces with a draggable gap between them. Rows inside those panes
are inset pills rather than full-bleed bars. Lucide icons, Inter for the
interface, restyled calendar, compose window, Address Book and Settings, with
colours that follow the current Omarchy theme.

## What's in here

| Path | Goes to |
|---|---|
| `files/chrome/*.css` | `<profile>/chrome/` (profile path filled in for `@CHROME_DIR@`) |
| `files/chrome/icons/lucide/` | `<profile>/chrome/icons/lucide/` |
| `files/user.js` | a marked block in `<profile>/user.js` |
| `files/fonts/Inter/` | `~/.local/share/fonts/Inter/` |
| `files/extensions/` | `<profile>/extensions/` (Send Later add-on) |
| `files/omarchy/thunderbird-colors` | `~/.config/omarchy/hooks/theme-set.d/` (bash stub) |
| `files/omarchy/thunderbird-colors.py` | `~/.config/omarchy/hooks/` (the recolour script the stub runs) |
| `files/omarchy/themes/trance/` | `~/.config/omarchy/themes/trance/` (only if missing, then applied) |

`<profile>` is found automatically: the profile Thunderbird actually starts
with (from `installs.ini`), in `~/.config/thunderbird`, `~/.thunderbird` or the
Flatpak location.

## How the styling is organised

- `theme-tokens.css` — every custom property: palette, corner radii, the pane
  gap, elevation, and the Lucide icon URLs. Change the look here first.
- `userChrome.css` — Thunderbird's own windows (3-pane, calendar, compose,
  menus, tooltips).
- `userContent.css` — the tabs that load as content pages (Address Book,
  Settings), scoped with `@-moz-document` so emails are never restyled.
- `omarchy-colors.css` — generated in the profile by the theme-set hook; it
  overrides the palette tokens with the current Omarchy theme's colours. The
  hook is split in two on purpose: `omarchy-hook` runs everything in
  `hooks/theme-set.d/` as `bash "$hook"`, ignoring shebangs, so the entry there
  is a bash stub and the Python it execs sits in `hooks/thunderbird-colors.py`.

The shape of the floating layout comes from three things: padding on the
`about:3pane` grid opens the outer gutter, the pane splitters are widened to
`--tr-gap` so the inner gaps stay draggable, and each pane gets
`--tr-radius-pane` plus `--tr-shadow-pane`. Adjust `--tr-gap` to tighten or
loosen the whole layout.

## Apply on a fresh install

1. Install Thunderbird, open it once so it creates a profile (set up your
   account if you like), then close it.
2. Run `./install.sh`.
3. Start Thunderbird. Turn on Send Later in menu > Add-ons and Themes.

`install.sh` is safe to re-run. It refuses to run while Thunderbird is open.

## After changing the theme on this machine

Run `./capture.sh` to copy the live files back into `files/`, then commit.

## Remove

`./uninstall.sh` removes the stylesheets, icons, preferences and Omarchy hook.
`./uninstall.sh --all` also removes the Inter font and Send Later.

## Notes

- Thunderbird only reads the theme at startup, so restart it after changes or
  an Omarchy theme switch.
- Everything is disabled under high-contrast mode (`prefers-contrast`).
- Menu corner radii need a compositor with transparency; Thunderbird squares
  menus off on Linux without it, and only the colours apply there.
- Email bodies are deliberately never restyled. In dark mode Thunderbird's own
  `mail.dark-reader.enabled` puts `color-scheme: dark` on message documents, so
  Gecko paints its default dark canvas behind a message that declares no
  background of its own. That backdrop is Thunderbird's, not this theme's; turn
  it off with the toggle at the top right of the message header.
- This repo was called `thunderbird-mailspring-theme` before; the install
  scripts still recognise that version's `user.js` marker, so upgrading in
  place replaces the old block instead of duplicating it.
- Icons are [Lucide](https://lucide.dev) (ISC). Inter is by Rasmus Andersson
  (SIL Open Font License, `files/fonts/Inter/LICENSE.txt`). Send Later 10.7.8 is
  from addons.thunderbird.net. Keep this repo private if you don't want to
  redistribute those.
