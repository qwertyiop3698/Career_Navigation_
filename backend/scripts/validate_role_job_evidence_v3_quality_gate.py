import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v3.csv"
DEFAULT_REPORT = ROOT_DIR / "data" / "exports" / "role_job_evidence_v3_quality_gate_report.md"
DEFAULT_DUPLICATES = ROOT_DIR / "data" / "exports" / "role_job_evidence_v3_duplicate_review.csv"
DEFAULT_SKILLS = ROOT_DIR / "data" / "exports" / "role_job_evidence_v3_suspicious_skill_review.csv"

TARGET_ROLES = [
    "AI Backend Developer",
    "Backend Developer",
    "Builder",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Frontend Developer",
]

SUSPICIOUS_SKILLS = {
    "Data Analyst": ["Go", "Embedding", "LLM", "RAG", "Spark", "Machine Learning"],
    "Frontend Developer": ["Java", "C++", "Go", "Python", "Kubernetes", "LLM", "Embedding"],
    "AI Backend Developer": ["Go", "Java", "Machine Learning", "React"],
    "Builder": ["AWS", "Machine Learning", "Java"],
}

PRIMARY_ADJACENT_SKILLS = {
    ("AI Backend Developer", "Machine Learning"),
}

DUPLICATE_FIELDS = [
    "role",
    "company",
    "normalized_title",
    "posting_count",
    "posting_ids",
    "urls",
    "locations",
    "location_differs",
    "departments",
    "text_similarity_min",
    "text_similarity_average",
    "final_skills_identical",
    "duplicate_status",
    "complete_duplicate_possible",
    "distinct_opening_possible",
    "rag_embedding_recommendation",
    "job_role_skill_evidence_recommendation",
]

SKILL_FIELDS = [
    "role",
    "skill",
    "accepted_role_count",
    "skill_posting_count",
    "skill_share_percent",
    "source_posting_id",
    "company",
    "title",
    "skills",
    "predicted_skills",
    "predicted_skill_scores",
    "final_skills",
    "skills_method",
    "direct_evidence_fields",
    "direct_evidence_excerpt",
    "evidence_status",
    "evidence_reason",
    "responsibilities_excerpt",
    "requirements_excerpt",
    "preferred_qualifications_excerpt",
    "job_url",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the final file-only quality gate for accepted role evidence v3."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--duplicate-output", type=Path, default=DEFAULT_DUPLICATES)
    parser.add_argument("--skill-output", type=Path, default=DEFAULT_SKILLS)
    args = parser.parse_args()

    rows = read_csv(args.input.resolve())
    grouped_by_role = group_by_role(rows)
    duplicate_groups = find_duplicate_groups(rows)
    skill_reviews, skill_summary = review_suspicious_skills(grouped_by_role)

    write_csv(args.duplicate_output.resolve(), DUPLICATE_FIELDS, duplicate_groups)
    write_csv(args.skill_output.resolve(), SKILL_FIELDS, skill_reviews)
    write_report(
        args.report_output.resolve(),
        args.input.resolve(),
        rows,
        grouped_by_role,
        duplicate_groups,
        skill_reviews,
        skill_summary,
    )
    print_summary(
        args.report_output.resolve(),
        args.duplicate_output.resolve(),
        args.skill_output.resolve(),
        rows,
        duplicate_groups,
        skill_summary,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def group_by_role(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    output: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        output[role_of(row)].append(row)
    return output


def find_duplicate_groups(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    company_role_rows: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        company_role_rows[(role_of(row), value(row, "company").lower())].append(row)

    results = []
    grouped_rows = []
    for (role, _company_key), candidate_rows in sorted(company_role_rows.items()):
        grouped_rows.extend((role, component) for component in similar_title_components(candidate_rows))

    for role, group_rows in grouped_rows:
        if len(group_rows) < 2:
            continue
        normalized_titles = sorted({normalize_title(value(row, "title")) for row in group_rows})
        normalized_title = " / ".join(normalized_titles)
        similarities = pairwise_similarities(group_rows)
        min_similarity = min(similarities) if similarities else 1.0
        average_similarity = sum(similarities) / len(similarities) if similarities else 1.0
        skills_identical = len({canonical_skills(row) for row in group_rows}) == 1
        texts_available = all(content_text(row) for row in group_rows)
        locations = sorted({value(row, "location") for row in group_rows if value(row, "location")})
        departments = sorted({value(row, "department") for row in group_rows if value(row, "department")})
        urls = sorted({value(row, "job_url") for row in group_rows if value(row, "job_url")})

        if (
            len(locations) > 1
            or len(departments) > 1
            or not skills_identical
            or (texts_available and min_similarity < 0.92)
        ):
            status = "distinct_opening_same_title"
            rag_recommendation = "May embed each opening, but cap same-company/title cards in UI results."
            score_recommendation = "Keep as separate market evidence unless manual review identifies cloned text."
        elif texts_available and skills_identical and min_similarity >= 0.985:
            status = "same_content_duplicate"
            rag_recommendation = "Embed one representative document; retain duplicate_group_id in metadata."
            score_recommendation = "Deduplicate to one posting before skill evidence aggregation."
        else:
            status = "needs_manual_review"
            rag_recommendation = "Do not embed all copies until manually checked; prefer one provisional representative."
            score_recommendation = "Exclude duplicates from scoring until manually resolved."

        results.append(
            {
                "role": role,
                "company": value(group_rows[0], "company"),
                "normalized_title": normalized_title,
                "posting_count": str(len(group_rows)),
                "posting_ids": "; ".join(value(row, "id") for row in group_rows),
                "urls": "; ".join(urls),
                "locations": "; ".join(locations),
                "location_differs": bool_text(len(locations) > 1),
                "departments": "; ".join(departments),
                "text_similarity_min": f"{min_similarity:.4f}",
                "text_similarity_average": f"{average_similarity:.4f}",
                "final_skills_identical": bool_text(skills_identical),
                "duplicate_status": status,
                "complete_duplicate_possible": bool_text(status == "same_content_duplicate"),
                "distinct_opening_possible": bool_text(status == "distinct_opening_same_title"),
                "rag_embedding_recommendation": rag_recommendation,
                "job_role_skill_evidence_recommendation": score_recommendation,
            }
        )
    return results


def similar_title_components(rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    components: list[list[dict[str, str]]] = []
    for row in rows:
        title = normalize_title(value(row, "title"))
        matching_index = None
        for index, component in enumerate(components):
            if any(title_similarity(title, normalize_title(value(member, "title"))) >= 0.93 for member in component):
                matching_index = index
                break
        if matching_index is None:
            components.append([row])
        else:
            components[matching_index].append(row)
    return components


def title_similarity(first: str, second: str) -> float:
    if first == second:
        return 1.0
    return SequenceMatcher(None, first, second).ratio()


def review_suspicious_skills(
    grouped_by_role: dict[str, list[dict[str, str]]],
) -> tuple[list[dict[str, str]], dict[tuple[str, str], dict]]:
    review_rows = []
    summary = {}
    for role, skills in SUSPICIOUS_SKILLS.items():
        role_rows = grouped_by_role.get(role, [])
        for skill in skills:
            matches = [row for row in role_rows if skill in parse_skills(value(row, "final_skills"))]
            statuses: Counter[str] = Counter()
            for row in matches:
                reviewed = review_skill_row(role, skill, row, len(role_rows), len(matches))
                review_rows.append(reviewed)
                statuses[reviewed["evidence_status"]] += 1
            summary[(role, skill)] = {
                "role_count": len(role_rows),
                "posting_count": len(matches),
                "share": pct(len(matches), len(role_rows)),
                "statuses": statuses,
            }
    return review_rows, summary


def review_skill_row(
    role: str,
    skill: str,
    row: dict[str, str],
    role_count: int,
    posting_count: int,
) -> dict[str, str]:
    direct_fields, evidence_excerpt = direct_evidence(skill, row)
    method = value(row, "skills_method")
    in_original_skills = skill in parse_skills(value(row, "skills"))
    in_predictions = skill in parse_skills(value(row, "predicted_skills"))

    if not direct_fields and method == "model" and in_predictions:
        status = "predicted_only_review"
        reason = "Skill is present through model prediction only and is not stated in available posting text."
    elif not direct_fields:
        status = "incidental_or_false_positive"
        reason = "Skill is in final_skills but no technical usage is confirmed in available posting text."
    elif (role, skill) in PRIMARY_ADJACENT_SKILLS:
        status = "verified_direct_evidence"
        reason = "Skill is directly stated and is aligned with the accepted role context."
    else:
        status = "acceptable_secondary_skill"
        reason = "Skill is directly evidenced, but should be treated as supporting rather than core role evidence."

    if skill == "Go" and in_original_skills and not direct_fields:
        reason = "Keyword extraction likely matched ordinary English 'go' rather than the Go programming language."

    return {
        "role": role,
        "skill": skill,
        "accepted_role_count": str(role_count),
        "skill_posting_count": str(posting_count),
        "skill_share_percent": f"{pct(posting_count, role_count):.1f}",
        "source_posting_id": value(row, "id"),
        "company": value(row, "company"),
        "title": value(row, "title"),
        "skills": value(row, "skills"),
        "predicted_skills": value(row, "predicted_skills"),
        "predicted_skill_scores": value(row, "predicted_skill_scores"),
        "final_skills": value(row, "final_skills"),
        "skills_method": method,
        "direct_evidence_fields": "; ".join(direct_fields),
        "direct_evidence_excerpt": evidence_excerpt,
        "evidence_status": status,
        "evidence_reason": reason,
        "responsibilities_excerpt": excerpt(value(row, "responsibilities")),
        "requirements_excerpt": excerpt(value(row, "requirements")),
        "preferred_qualifications_excerpt": excerpt(value(row, "preferred_qualifications")),
        "job_url": value(row, "job_url"),
    }


def direct_evidence(skill: str, row: dict[str, str]) -> tuple[list[str], str]:
    evidence_fields = []
    snippets = []
    for field in ["responsibilities", "requirements", "preferred_qualifications"]:
        text = value(row, field)
        match = technical_skill_match(skill, text)
        if match:
            evidence_fields.append(field)
            snippets.append(f"{field}: {context_snippet(text, match.start(), match.end())}")
    return evidence_fields, " | ".join(snippets)


def technical_skill_match(skill: str, text: str):
    if not text:
        return None
    if skill == "Go":
        patterns = [
            r"\bgolang\b",
            r"\bgo\s+(programming|language|developer|development|backend|services?)\b",
            r"\b(languages?|technologies|tech stack|proficiency|proficient|experience with|using|such as)\b.{0,100}\bgo\b",
            r"\bgo\b.{0,80}\b(language|backend|services?|development)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match
        return None
    pattern = {
        "C++": r"(?<![A-Za-z0-9+#.])C\+\+(?![A-Za-z0-9+#.-])",
        "Java": r"(?<![A-Za-z0-9+#.])Java(?![A-Za-z0-9+#.-])",
        "Embedding": r"\bembeddings?\b",
        "LLM": r"\bllms?\b|large language model",
        "RAG": r"\brag\b|retrieval[- ]augmented",
        "Machine Learning": r"\bmachine learning\b",
        "Kubernetes": r"\bkubernetes\b|\bk8s\b",
        "AWS": r"\baws\b|amazon web services",
        "React": r"\breact\b",
        "Spark": r"\bspark\b",
        "Python": r"\bpython\b",
    }.get(skill, rf"\b{re.escape(skill)}\b")
    return re.search(pattern, text, flags=re.IGNORECASE)


def write_report(
    path: Path,
    input_path: Path,
    rows: list[dict[str, str]],
    grouped_by_role: dict[str, list[dict[str, str]]],
    duplicate_groups: list[dict[str, str]],
    skill_reviews: list[dict[str, str]],
    skill_summary: dict[tuple[str, str], dict],
) -> None:
    duplicate_by_role: dict[str, list[dict[str, str]]] = defaultdict(list)
    for group in duplicate_groups:
        duplicate_by_role[group["role"]].append(group)
    lines = [
        "# Role Job Evidence v3 Final Quality Gate Report",
        "",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Input accepted CSV: `{input_path.as_posix()}`",
        f"- Accepted candidates inspected: {len(rows):,}",
        "- Safety: CSV read and report generation only. No database mutation, evidence rebuild, RAG write, embedding generation, or OpenAI call was executed.",
        "",
        "## A. Duplicate Posting Gate",
        "",
        "| Role | Accepted Rows | Repeated Groups | Same-Content Groups | Distinct Opening Groups | Manual Review Groups | Documents Reduced if Same-Content Groups Use One Representative |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for role in TARGET_ROLES:
        groups = duplicate_by_role.get(role, [])
        statuses = Counter(group["duplicate_status"] for group in groups)
        reduction = sum(
            int(group["posting_count"]) - 1
            for group in groups
            if group["duplicate_status"] == "same_content_duplicate"
        )
        lines.append(
            f"| {role} | {len(grouped_by_role.get(role, [])):,} | {len(groups):,} | "
            f"{statuses['same_content_duplicate']:,} | {statuses['distinct_opening_same_title']:,} | "
            f"{statuses['needs_manual_review']:,} | {reduction:,} |"
        )
    lines.extend(["", "### Repeated Group Detail", ""])
    if not duplicate_groups:
        lines.append("- No repeated company/title groups found.")
    else:
        lines.extend(
            [
                "| Role | Company | Normalized Title | Count | Similarity Min | Skills Same | Status | RAG Recommendation |",
                "|---|---|---|---:|---:|---|---|---|",
            ]
        )
        for group in duplicate_groups:
            lines.append(
                f"| {md(group['role'])} | {md(group['company'])} | {md(group['normalized_title'])} | "
                f"{group['posting_count']} | {group['text_similarity_min']} | {group['final_skills_identical']} | "
                f"{group['duplicate_status']} | {md(group['rag_embedding_recommendation'])} |"
            )

    lines.extend(
        [
            "",
            "## B. Suspicious Skill Gate",
            "",
            "Statuses:",
            "",
            "- The `skills` column is an upstream extracted value, not an independent raw requirement source; direct verification therefore uses the available `responsibilities`, `requirements`, and `preferred_qualifications` text fields.",
            "- `verified_direct_evidence`: explicitly stated and aligned with the role context.",
            "- `acceptable_secondary_skill`: explicitly stated, but should not be presented as a core role-defining skill.",
            "- `predicted_only_review`: inserted from model prediction without direct textual evidence.",
            "- `incidental_or_false_positive`: not technically evidenced or likely extracted from ordinary wording.",
            "",
            "| Role | Skill | Included Rows | Share | Verified Direct | Acceptable Secondary | Predicted Only Review | Incidental / False Positive |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for role, skills in SUSPICIOUS_SKILLS.items():
        for skill in skills:
            item = skill_summary[(role, skill)]
            statuses = item["statuses"]
            lines.append(
                f"| {role} | {skill} | {item['posting_count']:,} | {item['share']:.1f}% | "
                f"{statuses['verified_direct_evidence']:,} | {statuses['acceptable_secondary_skill']:,} | "
                f"{statuses['predicted_only_review']:,} | {statuses['incidental_or_false_positive']:,} |"
            )

    lines.extend(["", "### High-Risk Skill Samples", ""])
    high_risk = [
        row for row in skill_reviews if row["evidence_status"] in {"predicted_only_review", "incidental_or_false_positive"}
    ]
    for role, skills in SUSPICIOUS_SKILLS.items():
        for skill in skills:
            samples = [
                row for row in high_risk if row["role"] == role and row["skill"] == skill
            ][:3]
            if not samples:
                continue
            lines.extend([f"#### {role} / {skill}", ""])
            for row in samples:
                lines.extend(
                    [
                        f"- **{md(row['company'])} - {md(row['title'])}**: `{row['evidence_status']}`",
                        f"  - Method: {md(row['skills_method'])}; final_skills: {md(row['final_skills'])}",
                        f"  - Reason: {md(row['evidence_reason'])}",
                        "",
                    ]
                )

    lines.extend(
        [
            "## C. Recommended Data Policy",
            "",
            "### JobRoleSkillEvidence Population",
            "",
            "- Do not aggregate directly from all 735 accepted rows without a skill-quality adjustment.",
            "- Remove extra rows in `same_content_duplicate` groups before market-count aggregation.",
            "- Count `verified_direct_evidence` and `acceptable_secondary_skill` only when a suspicious skill is used; exclude `predicted_only_review` and `incidental_or_false_positive` occurrences from skill scoring unless manually approved.",
            "- Keep the role acceptance decision separate from individual skill verification: a valid job posting can still contain an unreliable extracted skill.",
            "",
            "### RAG Embedding Population",
            "",
            "- Start from accepted v3, but embed a single representative for each `same_content_duplicate` group.",
            "- Keep distinct openings if they differ materially, while limiting repeated same-company/title display in search results.",
            "- Add metadata fields `duplicate_group_id`, `duplicate_status`, `evidence_quality`, and `verified_skills` before indexing.",
            "- The RAG evidence card should display only `verified_skills`, not every value currently in `final_skills`.",
            "",
            "### UI Retrieval Policy",
            "",
            "- Limit evidence cards to one result per company and normalized title in a recommendation response.",
            "- Show a recommended skill only with documents where that skill is directly verified or approved as a secondary requirement.",
            "- Mark low-volume evidence roles as BETA when coverage is limited, particularly Builder and Data Analyst/Frontend coverage after final deduplication.",
            "",
            "### Progression Decision",
            "",
            "- accepted v3 is not yet final for scoring or embedding because suspected skill contamination must be removed or recorded as verified skills.",
            "- Produce a v4 evidence-ready dataset containing deduplication decisions and verified skill lists, then rebuild JobRoleSkillEvidence and RAG documents from exactly that dataset.",
            "- Do not execute embedding until the v4 membership and verified skill policy are approved.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(
    report_path: Path,
    duplicate_path: Path,
    skill_path: Path,
    rows: list[dict[str, str]],
    duplicate_groups: list[dict[str, str]],
    skill_summary: dict[tuple[str, str], dict],
) -> None:
    statuses = Counter(group["duplicate_status"] for group in duplicate_groups)
    duplicate_reduction = sum(
        int(group["posting_count"]) - 1
        for group in duplicate_groups
        if group["duplicate_status"] == "same_content_duplicate"
    )
    print("Role evidence v3 quality gate completed (files only; no DB write; no OpenAI call).")
    print(f"Accepted rows inspected: {len(rows)}")
    print(f"Duplicate review CSV: {duplicate_path}")
    print(f"Suspicious skill review CSV: {skill_path}")
    print(f"Markdown report: {report_path}")
    print(
        "Duplicate groups: "
        f"same_content={statuses['same_content_duplicate']}, "
        f"distinct_opening={statuses['distinct_opening_same_title']}, "
        f"manual_review={statuses['needs_manual_review']}; "
        f"representative-only reduction={duplicate_reduction}"
    )
    for (role, skill), item in skill_summary.items():
        status = item["statuses"]
        print(
            f"{role} / {skill}: {item['posting_count']} ({item['share']:.1f}%), "
            f"direct={status['verified_direct_evidence'] + status['acceptable_secondary_skill']}, "
            f"predicted_only={status['predicted_only_review']}, "
            f"false_positive={status['incidental_or_false_positive']}"
        )


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).lower()
    normalized = re.sub(r"\b(us|usa|canada|remote|hybrid|emea|apac)\b", " ", normalized)
    normalized = re.sub(r"\([^)]*(remote|canada|us|usa|hybrid)[^)]*\)", " ", normalized)
    normalized = re.sub(r"[^a-z0-9+#]+", " ", normalized)
    return " ".join(normalized.split())


def content_text(row: dict[str, str]) -> str:
    text = " ".join(
        value(row, field)
        for field in ["responsibilities", "requirements", "preferred_qualifications"]
    )
    return normalize_text(text)


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def pairwise_similarities(rows: list[dict[str, str]]) -> list[float]:
    similarities = []
    for index, first in enumerate(rows):
        for second in rows[index + 1 :]:
            similarities.append(SequenceMatcher(None, content_text(first), content_text(second)).ratio())
    return similarities


def canonical_skills(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(sorted(skill.lower() for skill in parse_skills(value(row, "final_skills"))))


def parse_skills(text: str) -> list[str]:
    return [part.strip() for part in text.split(";") if part.strip()]


def context_snippet(text: str, start: int, end: int, radius: int = 100) -> str:
    beginning = max(0, start - radius)
    ending = min(len(text), end + radius)
    return excerpt(text[beginning:ending], 230)


def excerpt(text: str, limit: int = 260) -> str:
    normalized = " ".join(text.split())
    return f"{normalized[:limit].rstrip()}..." if len(normalized) > limit else normalized


def role_of(row: dict[str, str]) -> str:
    return value(row, "validated_job_role_category") or value(row, "original_job_role_category")


def pct(count: int, total: int) -> float:
    return count / total * 100 if total else 0.0


def bool_text(value_: bool) -> str:
    return "true" if value_ else "false"


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def md(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
