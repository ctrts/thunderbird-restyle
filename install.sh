#!/usr/bin/env bash
# Apply the Thunderbird Restyle theme to this machine's Thunderbird profile.
# Safe to re-run. See README.md.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FILES="$REPO/files"
MARK_BEGIN="// >>> thunderbird-restyle (managed by install.sh)"
MARK_END="// <<< thunderbird-restyle"
# The markers this repo used before it was renamed, so an older install is
# recognised and replaced instead of being left behind as a duplicate block.
OLD_MARK_BEGIN="// >>> mailspring-modern (managed by install.sh)"
OLD_MARK_END="// <<< mailspring-modern"
STAMP=$(date +%Y%m%d-%H%M%S)

if pgrep -x thunderbird >/dev/null || pgrep -x thunderbird-bin >/dev/null; then
  echo "Thunderbird is running. Close it first, then run this again." >&2
  exit 1
fi

if ! PROFILE=$("$REPO/lib/find-profile"); then
  echo "No Thunderbird profile found." >&2
  echo "Open Thunderbird once so it creates one (you can set up your account), close it, then run this again." >&2
  exit 1
fi
CHROME="$PROFILE/chrome"
echo "Profile: $PROFILE"

# 1. Stylesheets and icons. Icon URLs need the absolute profile path, so the
#    stored copies use @CHROME_DIR@ as a placeholder.
mkdir -p "$CHROME/icons"
for css in "$FILES"/chrome/*.css; do
  target="$CHROME/$(basename "$css")"
  if [[ -f $target ]] && ! grep -qE "Thunderbird Restyle|Mailspring Modern" "$target"; then
    cp -p "$target" "$target.bak-$STAMP"
  fi
  sed "s|@CHROME_DIR@|$CHROME|g" "$css" >"$target"
done
rm -rf "$CHROME/icons/lucide"
cp -r "$FILES/chrome/icons/lucide" "$CHROME/icons/lucide"
echo "Installed stylesheets and $(ls "$CHROME/icons/lucide" | wc -l) icons"

# 2. Preferences go in a marked block of user.js so other lines survive.
#    Lines identical to the theme's are dropped from the rest (covers copies
#    made before the markers existed), as is the theme's own header comment
#    under any of its past names.
USERJS="$PROFILE/user.js"
rest=""
if [[ -f $USERJS ]]; then
  rest=$(awk -v b="$MARK_BEGIN" -v e="$MARK_END" -v ob="$OLD_MARK_BEGIN" -v oe="$OLD_MARK_END" '
    NR == FNR { theme[$0] = 1; next }
    $0 == b || $0 == ob { skip = 1; next }
    $0 == e || $0 == oe { skip = 0; next }
    /^\/\/ Load chrome\/userChrome\.css \(.* theme\)$/ { next }
    !skip && !($0 in theme && $0 != "")' "$FILES/user.js" "$USERJS")
fi
{
  if [[ -n ${rest//[$'\n\t ']/} ]]; then printf '%s\n\n' "$rest"; fi
  echo "$MARK_BEGIN"
  cat "$FILES/user.js"
  echo "$MARK_END"
} >"$USERJS.tmp"
mv "$USERJS.tmp" "$USERJS"

# Sender names are cached per message; bumping the cache version makes existing
# mail pick up the names-only display.
PREFS="$PROFILE/prefs.js"
if [[ -f $PREFS ]]; then
  cp -p "$PREFS" "$PREFS.bak-$STAMP"
  cur=$(sed -n 's/.*"mail\.displayname\.version", *\([0-9]*\).*/\1/p' "$PREFS" | head -1)
  sed -i '/"mail\.displayname\.version"/d' "$PREFS"
  echo "user_pref(\"mail.displayname.version\", $((${cur:-99} + 1)));" >>"$PREFS"
fi
echo "Installed preferences (user.js)"

# 3. Inter, the interface font, per user.
FONT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/Inter"
mkdir -p "$FONT_DIR"
cp "$FILES"/fonts/Inter/* "$FONT_DIR/"
if command -v fc-cache >/dev/null; then fc-cache -f "$FONT_DIR" >/dev/null 2>&1 || true; fi
echo "Installed Inter font"

# 4. Send Later. Thunderbird keeps sideloaded add-ons off until you allow them.
if compgen -G "$FILES/extensions/*.xpi" >/dev/null; then
  mkdir -p "$PROFILE/extensions"
  for xpi in "$FILES"/extensions/*.xpi; do
    [[ -f "$PROFILE/extensions/$(basename "$xpi")" ]] || cp "$xpi" "$PROFILE/extensions/"
  done
  echo "Installed Send Later (enable it in Thunderbird: menu > Add-ons and Themes)"
fi

# 5. Omarchy: put back bundled custom themes that are missing (and apply
#    them), then recolour Thunderbird whenever the Omarchy theme changes.
if command -v omarchy >/dev/null; then
  for theme in "$FILES"/omarchy/themes/*/; do
    [[ -d $theme ]] || continue
    name=$(basename "$theme")
    dest="$HOME/.config/omarchy/themes/$name"
    if [[ ! -d $dest ]]; then
      mkdir -p "$HOME/.config/omarchy/themes"
      cp -r "$theme" "$dest"
      echo "Restored Omarchy theme: $name"
      if omarchy theme set "$name" >/dev/null 2>&1; then
        echo "Applied Omarchy theme: $name"
      else
        echo "Could not apply $name automatically; run: omarchy theme set $name"
      fi
    fi
  done

  # omarchy-hook runs each file in hooks/<name>.d/ as `bash "$hook"`, so the
  # Python recolour script cannot live there: bash would read its shebang as a
  # comment and choke on the first import. Keep the script a directory up and
  # install a bash stub that execs it.
  install -Dm755 "$FILES/omarchy/thunderbird-colors.py" "$HOME/.config/omarchy/hooks/thunderbird-colors.py"
  omarchy hook install theme-set "$FILES/omarchy/thunderbird-colors" >/dev/null
  bash "$HOME/.config/omarchy/hooks/theme-set.d/thunderbird-colors" "$(omarchy theme current 2>/dev/null || echo current)"
  echo "Installed Omarchy theme hook (colours follow your Omarchy theme)"
else
  echo "Omarchy not found: skipped the theme hook (Thunderbird uses the built-in palette)"
fi

echo
echo "Done. Start Thunderbird to see the theme."
