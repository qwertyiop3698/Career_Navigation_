from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.services.external_jobs import ats_collectors  # noqa: E402
from app.services.external_jobs.ats_collectors import fetch_company_jobs  # noqa: E402
from app.services.external_jobs.companies import COMPANIES  # noqa: E402
from app.services.external_jobs.role_evidence_collection_targets import SKILL_READY_TARGETS  # noqa: E402
from collect_role_evidence_batch import candidate_role  # noqa: E402


DEFAULT_CURRENT_V4 = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v4.csv"
DEFAULT_RESCREEN_V4 = (
    ROOT_DIR
    / "data"
    / "exports"
    / "rescreen_batches"
    / "external_job_postings_role_evidence_v4_evidence_rescreen_20260527_01.csv"
)
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "collection"
DEFAULT_REPORT = DEFAULT_OUTPUT_DIR / "additional_public_boards_candidates_report.md"
DEFAULT_REVIEWED = DEFAULT_OUTPUT_DIR / "additional_public_boards_reviewed.json"

ats_collectors.REQUEST_TIMEOUT_SECONDS = 25

PRIORITY_ROLES = [
    "Frontend Developer",
    "Builder",
    "Data Analyst",
    "Data Engineer",
    "AI Backend Developer",
    "Backend Developer",
]
CURRENT_SKILL_READY = {
    "AI Backend Developer": 80,
    "Backend Developer": 87,
    "Builder": 21,
    "Data Analyst": 51,
    "Data Engineer": 53,
    "Data Scientist": 111,
    "Frontend Developer": 16,
}

# Candidate list is intentionally broader than the final reviewed output. The
# script verifies public ATS access and title matches before writing the JSON
# used by the isolated collector.
DEFAULT_CANDIDATE_BOARDS = [
    {"company": "1Password", "ats": "greenhouse", "slug": "1password"},
    {"company": "Algolia", "ats": "greenhouse", "slug": "algolia"},
    {"company": "Airwallex", "ats": "greenhouse", "slug": "airwallex"},
    {"company": "Benchling", "ats": "greenhouse", "slug": "benchling"},
    {"company": "Canva", "ats": "greenhouse", "slug": "canva"},
    {"company": "Coda", "ats": "greenhouse", "slug": "coda"},
    {"company": "Cohere", "ats": "greenhouse", "slug": "cohere"},
    {"company": "Coinbase", "ats": "greenhouse", "slug": "coinbase"},
    {"company": "Cockroach Labs", "ats": "greenhouse", "slug": "cockroachlabs"},
    {"company": "Contentful", "ats": "greenhouse", "slug": "contentful"},
    {"company": "Customer.io", "ats": "greenhouse", "slug": "customerio"},
    {"company": "Deel", "ats": "greenhouse", "slug": "deel"},
    {"company": "DigitalOcean", "ats": "greenhouse", "slug": "digitalocean98"},
    {"company": "HashiCorp", "ats": "greenhouse", "slug": "hashicorp"},
    {"company": "Hightouch", "ats": "greenhouse", "slug": "hightouch"},
    {"company": "Hugging Face", "ats": "greenhouse", "slug": "huggingface"},
    {"company": "Miro", "ats": "greenhouse", "slug": "miro"},
    {"company": "Pinecone", "ats": "greenhouse", "slug": "pinecone"},
    {"company": "Rippling", "ats": "greenhouse", "slug": "rippling"},
    {"company": "Sentry", "ats": "greenhouse", "slug": "sentry"},
    {"company": "Shopify", "ats": "greenhouse", "slug": "shopify"},
    {"company": "Sourcegraph", "ats": "greenhouse", "slug": "sourcegraph91"},
    {"company": "Stack Overflow", "ats": "greenhouse", "slug": "stackoverflow"},
    {"company": "ThoughtSpot", "ats": "greenhouse", "slug": "thoughtspot"},
    {"company": "Weights & Biases", "ats": "greenhouse", "slug": "weightsbiases"},
    {"company": "Yelp", "ats": "greenhouse", "slug": "yelp"},
    {"company": "Moment", "ats": "greenhouse", "slug": "moment"},
    {"company": "8VC", "ats": "ashby", "slug": "8vc"},
    {"company": "Anyscale", "ats": "ashby", "slug": "Anyscale"},
    {"company": "Attio", "ats": "ashby", "slug": "attio"},
    {"company": "Cedar", "ats": "ashby", "slug": "Cedar"},
    {"company": "Cerebras", "ats": "ashby", "slug": "Cerebras"},
    {"company": "Clay Labs", "ats": "ashby", "slug": "claylabs"},
    {"company": "Clerk", "ats": "ashby", "slug": "Clerk"},
    {"company": "ClickHouse", "ats": "ashby", "slug": "ClickHouse"},
    {"company": "Cognition", "ats": "ashby", "slug": "Cognition"},
    {"company": "Convex", "ats": "ashby", "slug": "Convex"},
    {"company": "Dagster Labs", "ats": "ashby", "slug": "Dagster Labs"},
    {"company": "Descript", "ats": "ashby", "slug": "Descript"},
    {"company": "Emidat", "ats": "ashby", "slug": "emidat"},
    {"company": "Fireworks AI", "ats": "ashby", "slug": "Fireworks AI"},
    {"company": "Flux", "ats": "ashby", "slug": "flux"},
    {"company": "Hex", "ats": "ashby", "slug": "Hex"},
    {"company": "Kota", "ats": "ashby", "slug": "kota"},
    {"company": "Lovable", "ats": "ashby", "slug": "Lovable"},
    {"company": "Mintlify", "ats": "ashby", "slug": "Mintlify"},
    {"company": "MotherDuck", "ats": "ashby", "slug": "MotherDuck"},
    {"company": "Neon", "ats": "ashby", "slug": "Neon"},
    {"company": "OpenAI", "ats": "ashby", "slug": "OpenAI"},
    {"company": "PlanetScale", "ats": "ashby", "slug": "PlanetScale"},
    {"company": "Rebar", "ats": "ashby", "slug": "rebar"},
    {"company": "Retool", "ats": "ashby", "slug": "Retool"},
    {"company": "Summation", "ats": "ashby", "slug": "summation"},
    {"company": "Turso", "ats": "ashby", "slug": "Turso"},
    {"company": "Valthos", "ats": "ashby", "slug": "valthos"},
    {"company": "White Circle", "ats": "ashby", "slug": "whitecircle"},
    {"company": "Windsurf", "ats": "ashby", "slug": "Windsurf"},
    {"company": "Canva", "ats": "lever", "slug": "canva"},
    {"company": "Sourcegraph", "ats": "lever", "slug": "sourcegraph"},
    {"company": "Tines", "ats": "lever", "slug": "tines"},
    {"company": "Turo", "ats": "lever", "slug": "turo"},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate candidate public ATS boards for role evidence expansion. "
            "No DB writes, embeddings, OpenAI calls, or batch collection outputs are performed."
        )
    )
    parser.add_argument("--candidates-json", type=Path, default=None)
    parser.add_argument("--current-v4", type=Path, default=DEFAULT_CURRENT_V4)
    parser.add_argument("--rescreen-v4", type=Path, default=DEFAULT_RESCREEN_V4)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--reviewed-output", type=Path, default=DEFAULT_REVIEWED)
    parser.add_argument("--max-reviewed-boards", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates = load_candidates(args.candidates_json)
    registered = registered_identities()
    existing_companies = registered["company_names"] | evidence_companies(
        [args.current_v4, args.rescreen_v4]
    )

    results = []
    for candidate in candidates:
        result = validate_candidate(candidate, registered, existing_companies)
        results.append(result)

    reviewed = select_reviewed_boards(results, args.max_reviewed_boards)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(build_report(results, reviewed), encoding="utf-8")
    args.reviewed_output.write_text(
        json.dumps(
            [
                {"company": item["company"], "ats": item["ats"], "slug": item["slug"]}
                for item in reviewed
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = {
        "candidate_boards_checked": len(results),
        "accessible_boards": sum(1 for item in results if item["public_board_accessible"]),
        "reviewed_boards": len(reviewed),
        "report": str(args.report_output),
        "reviewed_json": str(args.reviewed_output),
        "database_writes": False,
        "batch_collection_executed": False,
        "openai_calls": False,
        "embedding_requests": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def load_candidates(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return DEFAULT_CANDIDATE_BOARDS
    payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("--candidates-json must contain a list.")
    return payload


def registered_identities() -> dict[str, set[str]]:
    return {
        "board_keys": {(item["ats"], normalize_slug(item["slug"])) for item in COMPANIES},
        "company_names": {normalize_company(item["company"]) for item in COMPANIES},
    }


def evidence_companies(paths: list[Path]) -> set[str]:
    output: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        import csv

        with path.open("r", encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                company = row.get("company")
                if company:
                    output.add(normalize_company(company))
    return output


def validate_candidate(
    candidate: dict[str, str],
    registered: dict[str, set[str]],
    existing_companies: set[str],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    company = candidate["company"]
    ats = candidate["ats"]
    slug = candidate["slug"]
    board_key = (ats, normalize_slug(slug))
    company_key = normalize_company(company)
    already_registered = board_key in registered["board_keys"] or company_key in registered["company_names"]
    already_in_evidence = company_key in existing_companies

    base = {
        "company": company,
        "ats": ats,
        "slug": slug,
        "public_board_accessible": False,
        "public_job_count": 0,
        "checked_at": now,
        "already_registered": already_registered,
        "already_in_evidence": already_in_evidence,
        "matched_roles": [],
        "matched_role_counts": {},
        "matched_job_titles": [],
        "exclusion_title_hit": False,
        "exclusion_titles": [],
        "recommendation": "excluded",
        "reason": "",
        "fetch_error": "",
    }
    if already_registered:
        return {
            **base,
            "reason": "Already present in configured company boards; excluded from new candidates.",
        }

    try:
        jobs = fetch_company_jobs(candidate)
    except Exception as exc:
        return {**base, "reason": "Public board was not accessible.", "fetch_error": str(exc)}

    role_counts: Counter[str] = Counter()
    matched_titles: list[str] = []
    exclusion_titles: list[str] = []
    for job in jobs:
        title = job.get("title") or ""
        match = candidate_role(title)
        if not match:
            continue
        if match.get("excluded"):
            exclusion_titles.append(title)
            continue
        role = match["role"]
        if role == "Data Scientist":
            continue
        role_counts[role] += 1
        if len(matched_titles) < 10:
            matched_titles.append(f"{role}: {title}")

    total_matches = sum(role_counts.values())
    if total_matches == 0:
        recommendation = "excluded"
        reason = "Accessible board, but no current title matches for shortage roles."
    elif already_in_evidence:
        recommendation = "hold"
        reason = "Company already appears in current evidence data; hold unless diversity need remains."
    else:
        recommendation = "reviewed"
        reason = board_value_reason(role_counts)

    return {
        **base,
        "public_board_accessible": True,
        "public_job_count": len(jobs),
        "matched_roles": sorted(role_counts),
        "matched_role_counts": dict(sorted(role_counts.items())),
        "matched_job_titles": matched_titles,
        "exclusion_title_hit": bool(exclusion_titles),
        "exclusion_titles": exclusion_titles[:10],
        "recommendation": recommendation,
        "reason": reason,
    }


def board_value_reason(role_counts: Counter[str]) -> str:
    if role_counts.get("Frontend Developer"):
        return "Selected because Frontend Developer is the largest remaining shortage."
    if role_counts.get("Builder"):
        return "Selected because Builder has a severe shortage and matching product-building titles."
    if role_counts.get("Data Analyst"):
        return "Selected because Data Analyst still needs verified skill-ready evidence."
    if role_counts.get("Data Engineer"):
        return "Selected because Data Engineer still needs verified skill-ready evidence."
    if role_counts.get("AI Backend Developer"):
        return "Selected because AI Backend is close to target but still short."
    if role_counts.get("Backend Developer"):
        return "Selected for Backend company diversity rather than raw volume."
    return "Selected for shortage-role coverage."


def select_reviewed_boards(results: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    reviewed = [item for item in results if item["recommendation"] == "reviewed"]
    selected: list[dict[str, Any]] = []
    role_company_counts: Counter[str] = Counter()
    for item in sorted(reviewed, key=selection_key):
        roles = item["matched_role_counts"]
        primary = primary_role(roles)
        if primary and role_company_counts[primary] >= minimum_company_goal(primary):
            has_other_shortage = any(
                role != primary and role_company_counts[role] < minimum_company_goal(role)
                for role in roles
            )
            if not has_other_shortage:
                continue
        selected.append(item)
        for role in roles:
            role_company_counts[role] += 1
        if len(selected) >= limit:
            break
    return selected


def selection_key(item: dict[str, Any]) -> tuple[int, int, str]:
    role_counts = item["matched_role_counts"]
    priority = min((PRIORITY_ROLES.index(role) for role in role_counts if role in PRIORITY_ROLES), default=99)
    shortage_weight = sum(SKILL_READY_TARGETS[role] - CURRENT_SKILL_READY.get(role, 0) for role in role_counts)
    return (priority, -shortage_weight, item["company"].lower())


def primary_role(role_counts: dict[str, int]) -> str:
    if not role_counts:
        return ""
    return sorted(role_counts.items(), key=lambda item: (-item[1], PRIORITY_ROLES.index(item[0]) if item[0] in PRIORITY_ROLES else 99))[0][0]


def minimum_company_goal(role: str) -> int:
    if role == "Builder":
        return 12
    if role == "Frontend Developer":
        return 8
    return 5


def build_report(results: list[dict[str, Any]], reviewed: list[dict[str, Any]]) -> str:
    accessible = [item for item in results if item["public_board_accessible"]]
    role_raw_counts: Counter[str] = Counter()
    role_company_counts: defaultdict[str, set[str]] = defaultdict(set)
    for item in reviewed:
        for role, count in item["matched_role_counts"].items():
            role_raw_counts[role] += count
            role_company_counts[role].add(item["company"])

    reviewed_keys = {(item["ats"], item["slug"]) for item in reviewed}
    lines = [
        "# Additional Public ATS Board Candidates",
        "",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- Scope: candidate board validation only. No DB writes, no batch collection, no OpenAI calls, no embeddings.",
        f"- Candidate boards checked: {len(results)}",
        f"- Accessible boards: {len(accessible)}",
        f"- Reviewed JSON boards selected: {len(reviewed)}",
        "",
        "## Status Definitions",
        "",
        "- `selected_for_batch`: included in `additional_public_boards_reviewed.json` and will be collected if the isolated batch is approved.",
        "- `reserve_candidate`: accessible and matched shortage-role titles, but not included in the current JSON to keep this batch focused.",
        "- `excluded`: inaccessible, already configured, already in evidence, or no current shortage-role title matches.",
        "",
        "## Reviewed Selection Summary",
        "",
        "| Role | Current Skill-Ready | Target | Shortage | Additional Raw Title Matches | New Company Count |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for role in PRIORITY_ROLES:
        current = CURRENT_SKILL_READY[role]
        target = SKILL_READY_TARGETS[role]
        lines.append(
            f"| {role} | {current} | {target} | {max(0, target - current)} | "
            f"{role_raw_counts.get(role, 0)} | {len(role_company_counts.get(role, set()))} |"
        )

    lines.extend(
        [
            "",
            "## Final Reviewed Boards",
            "",
            "| Company | ATS | Slug | Jobs | Matched Roles | Sample Matched Titles | Reason |",
            "|---|---|---|---:|---|---|---|",
        ]
    )
    for item in reviewed:
        lines.append(
            f"| {item['company']} | {item['ats']} | `{item['slug']}` | {item['public_job_count']} | "
            f"{format_counts(item['matched_role_counts'])} | {html_join(item['matched_job_titles'])} | "
            f"{item['reason']} |"
        )

    lines.extend(
        [
            "",
            "## All Candidates Checked",
            "",
            "| Company | ATS | Slug | Accessible | Jobs | Recommendation | Matched Roles | Exclusion Hit | Reason/Error |",
            "|---|---|---|---|---:|---|---|---|---|",
        ]
    )
    for item in results:
        display_status = display_recommendation(item, reviewed_keys)
        reason = item["reason"] or item["fetch_error"]
        if item["fetch_error"]:
            reason = f"{reason}: {item['fetch_error']}"
        lines.append(
            f"| {item['company']} | {item['ats']} | `{item['slug']}` | "
            f"{str(item['public_board_accessible']).lower()} | {item['public_job_count']} | "
            f"{display_status} | {format_counts(item['matched_role_counts'])} | "
            f"{str(item['exclusion_title_hit']).lower()} | {escape_pipe(reason)} |"
        )

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            "- Run an isolated additional batch only after reviewing `additional_public_boards_reviewed.json`.",
            "- Frontend and Builder remain the first priority because local re-screening left the largest shortages.",
            "- Backend boards are selected only when they add new company diversity.",
            "- The batch output must still pass v3 and v4; raw title matches are not final evidence.",
            "",
            "```powershell",
            "$batch = 'evidence_boost_20260529_01'",
            "python backend/scripts/collect_role_evidence_batch.py --execute --batch-id $batch --additional-companies-json backend/data/collection/additional_public_boards_reviewed.json",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def display_recommendation(item: dict[str, Any], reviewed_keys: set[tuple[str, str]]) -> str:
    if (item["ats"], item["slug"]) in reviewed_keys:
        return "selected_for_batch"
    if item["recommendation"] == "reviewed":
        return "reserve_candidate"
    return "excluded"


def format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{role}: {count}" for role, count in counts.items()) or "-"


def html_join(items: list[str]) -> str:
    return "<br>".join(escape_pipe(item) for item in items) or "-"


def escape_pipe(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def normalize_company(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower().replace("&", "and"))


def normalize_slug(value: str) -> str:
    return value.strip().lower()


if __name__ == "__main__":
    raise SystemExit(main())
