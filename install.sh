#!/bin/sh
# Installs Desktop Pets into the Codex pets folder (macOS / Linux).
# Usage: curl -fsSL https://raw.githubusercontent.com/60jong/desktop-pets/main/install.sh | sh
# Pick specific pets: DESKTOP_PETS="sprouty,mochi" sh install.sh
set -eu

REPO_RAW_URL="https://raw.githubusercontent.com/60jong/desktop-pets/main"
AVAILABLE_PETS="sprouty mochi agoumon"
REQUESTED_PETS=$(printf '%s' "${DESKTOP_PETS:-$AVAILABLE_PETS}" | tr ',' ' ')
PETS_ROOT="${CODEX_HOME:-$HOME/.codex}/pets"

for pet in $REQUESTED_PETS; do
  case " $AVAILABLE_PETS " in
    *" $pet "*) ;;
    *) echo "Unknown pet '$pet'. Choose from: $AVAILABLE_PETS" >&2; exit 1 ;;
  esac
  mkdir -p "$PETS_ROOT/$pet"
  for file in pet.json spritesheet.png; do
    curl -fsSL "$REPO_RAW_URL/pets/$pet/$file" -o "$PETS_ROOT/$pet/$file"
  done
  echo "Installed $pet -> $PETS_ROOT/$pet"
done

echo "Done. Restart Codex and pick the pet from its pet list."
