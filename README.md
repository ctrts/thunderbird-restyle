# Mailspring Modern for Thunderbird

A Mailspring-style theme for Thunderbird on Omarchy: flat message list, Lucide
icons, Inter font, restyled calendar, compose window, Address Book and
Settings, with colours that follow the current Omarchy theme.

## What's in here

| Path | Goes to |
|---|---|
| `files/chrome/*.css` | `<profile>/chrome/` (profile path filled in for `@CHROME_DIR@`) |
| `files/chrome/icons/lucide/` | `<profile>/chrome/icons/lucide/` |
| `files/user.js` | a marked block in `<profile>/user.js` |
| `files/fonts/Inter/` | `~/.local/share/fonts/Inter/` |
| `files/extensions/` | `<profile>/extensions/` (Send Later add-on) |
| `files/omarchy/thunderbird-colors` | `~/.config/omarchy/hooks/theme-set.d/` |
| `files/omarchy/themes/trance/` | `~/.config/omarchy/themes/trance/` (only if missing, then applied) |

`<profile>` is found automatically: the profile Thunderbird actually starts
with (from `installs.ini`), in `~/.config/thunderbird`, `~/.thunderbird` or the
Flatpak location.

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
- Icons are [Lucide](https://lucide.dev) (ISC). Inter is by Rasmus Andersson
  (SIL Open Font License, `files/fonts/Inter/LICENSE.txt`). Send Later 10.7.8 is
  from addons.thunderbird.net. Keep this repo private if you don't want to
  redistribute those.
