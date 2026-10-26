#!/usr/bin/env python3
"""
sean_infer_artifacts.py — AI 在 sean plan 阶段推断产物的规则引擎。

把 SKILL.md 里的推断规则变成可执行的启发式：读需求文档的
Behaviors + Acceptance Criteria + Problem，输出建议的产物清单。

这是给 AI 的"脚手架"——AI 可以覆盖它的输出，但默认按这个来，
避免"为了显得周到而编造产物"。

用法:
  python sean_infer_artifacts.py --requirement docs/requirements/2026-10-12-auth.md
  python sean_infer_artifacts.py --requirement <path> --project <root>

输出: JSON 数组，每项 {type, path, inferred_from}
退出码: 0
"""

import argparse
import json
import re
import sys
from pathlib import Path


# 推断规则：需求里的信号 → 产物类型
# 第一层：显式关键词（需求直接说了"建表""初始化数据"）
# 第二层：语义信号（需求用业务语言描述了需要存储/批处理/配置的场景）
# 两层都命中才推断 —— 只有显式关键词会漏掉业务化表述，
# 只有语义信号会在"只是查询一下"这类场景误报。
INFERENCE_RULES = [
    ("database", {
        # 显式：需求直接提到数据层
        "explicit": [
            r"存储", r"表结构", r"建表", r"字段", r"关联关系", r"索引",
            r"迁移", r"schema", r"migrat", r"\btable\b", r"\bcolumn\b",
            r"持久化", r"数据库",
        ],
        # 语义：需求描述了"需要记住某个实体"的场景
        "semantic": [
            r"注册", r"账号", r"用户表", r"入库", r"保存.*(记录|信息|数据)",
            r"(添加|新增|创建).*(用户|订单|商品|记录|条目)",
            r"(编辑|修改|更新).*(信息|资料|数据)",
            r"(查看|查询|列出).*(所有|全部).*(用户|订单|记录|列表)",
            r"唯一", r"主键", r"外键",
        ],
        "reason": "需求涉及实体存储 → 需建表/迁移 SQL",
    }),
    ("batch", {
        "explicit": [
            r"初始化数据", r"种子数据", r"seed", r"迁移历史数据", r"数据迁移",
            r"定时任务", r"批量处理", r"批处理", r"导入", r"清洗脚本",
            r"cron", r"\bscript\b",
        ],
        "semantic": [
            r"初始化.*(管理员|账号|数据|用户)",
            r"(管理员|超级用户).*(创建|初始化|默认)",
            r"(每天|定时|定期|周期).*(执行|运行|处理)",
            r"(批量|大量).*(数据|记录|导入|处理)",
            r"(清理|归档).*(旧|历史|过期).*(数据|记录)",
        ],
        "reason": "需求涉及数据初始化/批处理 → 需批处理脚本",
    }),
    ("config", {
        "explicit": [
            r"密钥", r"配置项", r"环境变量", r"连接串", r"模板",
            r"secret", r"\bconfig\b", r"\.env", r"token.*配置",
        ],
        "semantic": [
            r"JWT", r"(令牌|token).*(签发|生成|校验|配置)",
            r"(签名|加密|解密).*(密钥|key|secret)",
            r"(数据库|DB|Redis|缓存).*(连接|地址|url|dsn)",
            r"(第三方|外部|API).*(key|密钥|凭证|凭据)",
        ],
        "reason": "需求涉及密钥/配置 → 需配置模板",
    }),
]
# 项目自身的路径约定（AI 应优先遵循 AGENTS.md，这里给默认值）
DEFAULT_PATH_TEMPLATES = {
    "database": "migrations/{seq:03d}_{slug}.sql",
    "batch": "scripts/{slug}.sh",
    "config": "config/{slug}.template",
}


def slugify(text: str) -> str:
    """Make a short kebab-case slug from text.

    Keeps ASCII words; for CJK, uses the feature name instead (passed in
    separately) because transliterating arbitrary Chinese is not useful.
    """
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    if words:
        return "_".join(words[:4])
    return ""


def detect_project_convention(project_root: Path, art_type: str) -> str | None:
    """Detect the project's own path convention for this artifact type."""
    candidates = {
        "database": ["migrations", "db/migrations", "alembic/versions", "sql"],
        "batch": ["scripts", "bin", "tools"],
        "config": ["config", "configs", "settings"],
    }
    for c in candidates.get(art_type, []):
        if (project_root / c).is_dir():
            return c
    return None


def extract_sections(requirement_text: str) -> dict:
    """Extract Problem / Behaviors / Acceptance Criteria from the requirement."""
    sections = {}
    current = None
    buf = []
    for line in requirement_text.splitlines():
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            if current:
                sections[current] = "\n".join(buf)
            current = m.group(1).strip()
            buf = []
        elif current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf)
    return sections


def infer(requirement_text: str, project_root: Path, feature_name: str) -> list[dict]:
    """Infer artifacts from the requirement text."""
    sections = extract_sections(requirement_text)
    signals = "\n".join([
        sections.get("Problem", ""),
        sections.get("Behaviors", ""),
        sections.get("Acceptance Criteria", ""),
    ])

    results = []
    for art_type, rule in INFERENCE_RULES:
        # 两层信号：显式命中即可推断；语义命中也推断（并标注来源层）
        matched_signal = None
        signal_layer = None

        for layer in ("explicit", "semantic"):
            for p in rule[layer]:
                m = re.search(p, signals, re.IGNORECASE)
                if m:
                    for line in signals.splitlines():
                        if re.search(p, line, re.IGNORECASE):
                            matched_signal = line.strip().lstrip("- ").strip()
                            signal_layer = layer
                            break
                    if matched_signal:
                        break
            if matched_signal:
                break

        if not matched_signal:
            continue

        conv = detect_project_convention(project_root, art_type)
        # slug 用 feature 名 + 类型限定词，不用触发行（触发行可能很长或含中文）
        base = slugify(feature_name) or "artifact"
        qualifier = {"database": "schema", "batch": "init", "config": "settings"}[art_type]
        slug = f"{base}_{qualifier}"

        if art_type == "database":
            if conv and conv != "migrations":
                # alembic/versions 等非标准目录：python 文件，不带序号
                path = f"{conv}/{slug}.py"
            else:
                path = f"migrations/001_{slug}.sql"
        else:
            d = conv or {"batch": "scripts", "config": "config"}[art_type]
            ext = "sh" if art_type == "batch" else "template"
            path = f"{d}/{slug}.{ext}"

        results.append({
            "type": art_type,
            "path": path,
            "inferred_from": matched_signal,
            "signal_layer": signal_layer,
            "reason": rule["reason"],
            "project_convention_detected": conv,
        })

    return results


def main():
    ap = argparse.ArgumentParser(description="Infer artifacts from a requirement")
    ap.add_argument("--requirement", required=True, help="requirement markdown path")
    ap.add_argument("--project", default=".", help="project root (for convention detection)")
    ap.add_argument("--feature", default="", help="feature name (for output clarity)")
    args = ap.parse_args()

    req_path = Path(args.requirement)
    if not req_path.exists():
        print(f"ERROR: requirement not found: {req_path}", file=sys.stderr)
        sys.exit(2)

    text = req_path.read_text(encoding="utf-8")
    results = infer(text, Path(args.project).resolve(), args.feature)

    if not results:
        print(json.dumps([], indent=2, ensure_ascii=False))
        sys.exit(0)

    print(json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
