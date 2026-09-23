#!/bin/bash
# sean-skills installer
# Usage: bash install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$SCRIPT_DIR/SKILL.md"
INSTALL_DIR="${HOME}/.hermes/skills/your-skills/sean"
mkdir -p "$INSTALL_DIR"

if [ ! -f "$SKILL_SRC" ]; then
    echo "ERROR: SKILL.md not found in $SCRIPT_DIR"
    exit 1
fi

cp "$SKILL_SRC" "$INSTALL_DIR/SKILL.md"
echo "✅ sean skill installed to $INSTALL_DIR"
echo ""
echo "Available commands:"
echo "  sean start <name>           - Create requirement"
echo "  sean plan <name>            - Generate TDD plan"
echo "  sean run <name> [--dry-run] [--no-fix] - Execute plan"
echo "  sean task <name> <N>        - Execute single task"
echo "  sean fix [name]             - Fix recent failure"
echo "  sean undo [name] [steps]    - Undo last operation"
echo "  sean list                   - List all features"
echo "  sean status <name>          - Show feature details"
echo "  sean report [name]          - Test report"
echo "  sean switch <name>          - Switch active feature"
echo "  sean clean                  - Clean state"
