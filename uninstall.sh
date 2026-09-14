#!/usr/bin/env bash
# Remove the Mailspring Modern theme. Pass --all to also remove the Inter font
# and the Send Later add-on. See README.md.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FILES="$REPO/files"
MARK_BEGIN="// >>> mailspring-modern (managed by install.sh)"
MARK_END="// <<< mailspring-modern"
STAMP=$(date +%Y%m%d-%H%M%S)
ALL=0
[[ ${1:-} == --all ]] && ALL=1

if pgrep -x thunderbird >/dev/null || pgrep -x thunderbird-bin >/dev/null; then
  echo "Thunderbird is running. Close it first, then run this again." >&2
  exit 1
fi

if PROFILE=$("$REPO/lib/find-profile"); then
  CHROME="$PROFILE/chrome"
  echo "Profile: $PROFILE"

  rm -f "$CHROME"/{userChrome.css,userContent.css,theme-tokens.css,omarchy-colors.css}
  rm -rf "$CHROME/icons/lucide"
  rmdir "$CHROME/icons" "$CHROME" 2>/dev/null || true
  echo "Removed stylesheets and icons"

  USERJS="$PROFILE/user.js"
  if [[ -f $USERJS ]]; then
    rest=$(awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
      NR == FNR { theme[$0] = 1; next }
      $0 == b { skip = 1; next }
      $0 == e { skip = 0; next }
      !skip && !($0 in theme && $0 != "")' "$FILES/user.js" "$USERJS")
    if [[ -n ${rest//[$'\n\t ']/} ]]; then
      printf '%s\n' "$rest" >"$USERJS"
    else
      rm -f "$USERJS"
    fi
  fi

  # Prefs set by user.js stay in prefs.js after user.js is gone; drop them so
  # Thunderbird's defaults come back, and refresh cached sender names.
  PREFS="$PROFILE/prefs.js"
  if [[ -f $PREFS ]]; then
    cp -p "$PREFS" "$PREFS.bak-$STAMP"
    sed -n 's/^user_pref("\([^"]*\)".*/\1/p' "$FILES/user.js" | while read -r name; do
      sed -i "/\"${name//./\\.}\"/d" "$PREFS"
    done
    cur=$(sed -n 's/.*"mail\.displayname\.version", *\([0-9]*\).*/\1/p' "$PREFS" | head -1)
    sed -i '/"mail\.displayname\.version"/d' "$PREFS"
    echo "user_pref(\"mail.displayname.version\", $((${cur:-99} + 1)));" >>"$PREFS"
  fi
  echo "Removed preferences"

  if ((ALL)); then
    for xpi in "$FILES"/extensions/*.xpi; do
      rm -f "$PROFILE/extensions/$(basename "$xpi")"
    done
    echo "Removed Send Later"
  fi
else
  echo "No Thunderbird profile found; skipping profile files."
fi

rm -f "$HOME/.config/omarchy/hooks/theme-set.d/thunderbird-colors"
echo "Removed Omarchy theme hook"

if ((ALL)); then
  rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/fonts/Inter"
  if command -v fc-cache >/dev/null; then fc-cache -f >/dev/null 2>&1 || true; fi
  echo "Removed Inter font"
fi

echo
echo "Done. Start Thunderbird to see its default look."
