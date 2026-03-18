#!/usr/bin/env python3
"""Update docs/vv-test-plan.md section 13 (Test Execution Summary) with CI test results.

Usage (from repo root):
    python scripts/update_vv_plan.py \\
        --python-unit=pass \\
        --integration=pass \\
        --js=pass \\
        --skills=pass \\
        --e2e=blocked \\
        --browser=blocked

Choices for each suite: pass | fail | blocked
- pass    -> ✅ **Approved**   (tests ran and all passed)
- fail    -> ❌ **Rejected**   (tests ran and one or more failed)
- blocked -> 🚧 **Blocked**   (suite could not run, e.g. Docker unavailable)

Manual-only TCs (Test Type = "Manual") always get ⬛ **Not Executed**.

Only section 13 is modified. Sections 11, 12 and all other content are untouched.
"""

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

# ── Status constants ──────────────────────────────────────────────────────────
STATUS_APPROVED = "✅ **Approved**"
STATUS_REJECTED = "❌ **Rejected**"
STATUS_BLOCKED = "🚧 **Blocked**"
STATUS_NOT_EXECUTED = "⬛ **Not Executed**"

# Maps Test Type keywords (column 3) to the CLI argument name
SUITE_MAP = {
    "JS Unit": "js",
    "Python Unit": "python_unit",
    "Integration": "integration",
    "E2E": "e2e",
    "Browser": "browser",
    "Skills": "skills",
    "Manual": "manual",
}


def determine_status(test_type: str, results: dict) -> str:
    """Return the status emoji+bold string for a TC given its Test Type value."""
    if test_type.strip() == "Manual":
        return STATUS_NOT_EXECUTED

    parts = [p.strip() for p in test_type.split("+")]
    statuses = []
    for part in parts:
        suite = SUITE_MAP.get(part)
        if suite is None:
            continue
        result = results.get(suite, "blocked")
        if result == "fail":
            statuses.append(STATUS_REJECTED)
        elif result == "blocked":
            statuses.append(STATUS_BLOCKED)
        else:
            statuses.append(STATUS_APPROVED)

    if not statuses:
        return STATUS_NOT_EXECUTED

    # Worst-case wins: Rejected > Blocked > Approved
    if STATUS_REJECTED in statuses:
        return STATUS_REJECTED
    if STATUS_BLOCKED in statuses:
        return STATUS_BLOCKED
    return STATUS_APPROVED


def update_file(path: Path, results: dict, today: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    in_section_13 = False
    in_table = False
    counts = {STATUS_APPROVED: 0, STATUS_REJECTED: 0,
              STATUS_BLOCKED: 0, STATUS_NOT_EXECUTED: 0}

    for line in lines:
        # ── Detect section 13 ─────────────────────────────────────────────────
        if "## 13. Test Execution Summary" in line:
            in_section_13 = True
            new_lines.append(line)
            continue

        # ── Detect summary table header (only inside section 13) ──────────────
        if in_section_13 and not in_table and "| TC ID |" in line and "Status" in line:
            in_table = True
            new_lines.append(line)
            continue

        # ── Process TC data rows ───────────────────────────────────────────────
        if in_table and line.strip().startswith("| TC-"):
            cols = [c.strip() for c in line.split("|")]
            # Expected: ['', tc_id, category, test_type, executed_by, date, status, notes, '']
            if len(cols) >= 9:
                test_type = cols[3]
                status = determine_status(test_type, results)
                counts[status] = counts.get(status, 0) + 1

                # Update date and executed-by for manual/not-executed rows
                if status == STATUS_NOT_EXECUTED:
                    cols[5] = "—"
                    cols[4] = "—"
                else:
                    cols[5] = today

                cols[6] = status
                new_lines.append("| " + " | ".join(cols[1:-1]) + " |")
                continue

        # ── Separator row — pass through unchanged ────────────────────────────
        if in_table and line.strip().startswith("| ---"):
            new_lines.append(line)
            continue

        # ── End of table when we hit a non-pipe line ──────────────────────────
        if in_table and not line.strip().startswith("|"):
            in_table = False

        new_lines.append(line)

    content = "\n".join(new_lines)
    if not content.endswith("\n"):
        content += "\n"

    # ── Update "Test run date" header line ────────────────────────────────────
    content = re.sub(
        r"\*\*Test run date\*\*:.*?—",
        f"**Test run date**: {today} —",
        content,
    )

    # ── Rebuild "Results" summary line ───────────────────────────────────────
    approved = counts.get(STATUS_APPROVED, 0)
    rejected = counts.get(STATUS_REJECTED, 0)
    blocked = counts.get(STATUS_BLOCKED, 0)
    not_exec = counts.get(STATUS_NOT_EXECUTED, 0)
    total_auto = approved + rejected + blocked

    result_parts = f"**{approved} ✅ Approved, {rejected} ❌ Rejected"
    if blocked:
        result_parts += f", {blocked} 🚧 Blocked"
    result_parts += "**"

    new_results_line = (
        f"**Results**: {total_auto} TCs verified across automated suites — "
        f"{result_parts}. "
        f"{not_exec} TC{'s' if not_exec != 1 else ''} require manual execution."
    )
    content = re.sub(r"\*\*Results\*\*:.*?execution\.", new_results_line, content)

    path.write_text(content, encoding="utf-8")
    print(
        f"Updated {path}: {approved} Approved, {rejected} Rejected, "
        f"{blocked} Blocked, {not_exec} Not Executed"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update V&V plan Test Execution Summary with CI test results"
    )
    for suite in ("python-unit", "integration", "js", "skills", "e2e", "browser"):
        parser.add_argument(
            f"--{suite}",
            choices=["pass", "fail", "blocked"],
            required=True,
            metavar="pass|fail|blocked",
        )
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Date in YYYY-MM-DD format (default: today UTC)",
    )
    args = parser.parse_args()

    results = {
        "python_unit": args.python_unit,
        "integration": args.integration,
        "js": args.js,
        "skills": args.skills,
        "e2e": args.e2e,
        "browser": args.browser,
    }

    vv_plan = Path("docs/vv-test-plan.md")
    if not vv_plan.exists():
        print(f"ERROR: {vv_plan} not found. Run from the repo root.")
        raise SystemExit(1)

    update_file(vv_plan, results, args.date)


if __name__ == "__main__":
    main()