#!/bin/bash
# sean-skills installer
# Usage: bash install.sh [install_dir]
#
# 安装内容：
#   SKILL.md      路由主文件（唯一常驻上下文）
#   references/   命令流程，按需加载
#   templates/    文档模板
#   scripts/      state 引擎与工具脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$SCRIPT_DIR/SKILL.md"
INSTALL_DIR="${1:-${HOME}/.hermes/skills/your-skills/sean}"

if [ ! -f "$SKILL_SRC" ]; then
    echo "ERROR: SKILL.md not found in $SCRIPT_DIR"
    exit 1
fi

mkdir -p "$INSTALL_DIR"
cp "$SKILL_SRC" "$INSTALL_DIR/SKILL.md"

for sub in references templates scripts; do
    if [ -d "$SCRIPT_DIR/$sub" ]; then
        mkdir -p "$INSTALL_DIR/$sub"
        cp -R "$SCRIPT_DIR/$sub/." "$INSTALL_DIR/$sub/"
        echo "  installed $sub -> $INSTALL_DIR/$sub"
    fi
done

chmod +x "$INSTALL_DIR"/scripts/*.py 2>/dev/null || true
rm -rf "$INSTALL_DIR"/scripts/__pycache__ 2>/dev/null || true

cat <<'EOF'

sean skill installed.

建议在 shell 里加个别名，省去每次拼脚本路径：
  alias sean-state='python3 ~/.hermes/skills/your-skills/sean/scripts/sean_state.py'

Available commands:
  sean init <project>             - Initialize project (conventions + onboarding)
  sean start <name> [desc...]     - Create requirement
  sean plan <name>                - Generate TDD plan
  sean run <name> [--dry-run] [--lite]
                                  - Execute plan (TDD + regression + handoff)
  sean task <name> <N>            - Execute single task
  sean dispatch <plan> [--fmt]    - Group tasks into dependency waves
  sean handoff <name> [--lite]    - Generate handoff document
  sean sync <name>                - Recover state from test reports
  sean review <name>              - Diff-based self-review + five-dimension assessment
  sean learn <name>               - Extract reusable patterns from history
  sean findings [name]            - View/manage findings
  sean fix [name]                 - Fix recent failure
  sean bug <name> [desc]          - Record/fix post-run bug (test-first)
  sean artifact <name> <act>      - Execute/verify artifacts (dry-run by default)
  sean undo [name] [steps]        - Undo (state via script, files via git)
  sean retry <name>               - Retry recent failure
  sean list / status / report / switch / export / clean

Optional (multi-platform consistency, off by default):
  python3 <skill>/scripts/sean_state.py detect-targets
  python3 <skill>/scripts/sean_parity.py --feature <name>
EOF
