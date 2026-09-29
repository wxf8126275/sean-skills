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
echo "  sean init <project>           - Initialize project (conventions + onboarding)"
echo "  sean start <name> [desc...]   - Create requirement"
echo "  sean plan <name>              - Generate TDD plan"
echo "  sean run <name> [--dry-run]   - Execute plan (TDD + regression + handoff)"
echo "  sean task <name> <N>          - Execute single task"
echo "  sean handoff <name>           - Generate handoff document for next AI"
echo "  sean sync <name>              - Recover state from test reports"
echo "  sean review <name>            - Five-dimension assessment + code review + findings"
echo "  sean learn <name>             - Extract reusable patterns from history"
echo "  sean findings [name]          - View/manage Agent Work Loop findings"
echo "  sean fix [name]               - Fix recent failure"
echo "  sean undo [name] [steps]      - Undo last operation"
echo "  sean retry <name>             - Retry recent failure"
echo "  sean list                     - List all features"
echo "  sean status <name>            - Show feature details"
echo "  sean report [name]            - Test report summary"
echo "  sean switch <name>            - Switch active feature"
echo "  sean export <name> --format <f> - Export to other agent formats"
echo "  sean clean [--keep-reports]   - Clean state"
