import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_analysis_ml_skills_v2.csv"
DEFAULT_ACCEPTED = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v3.csv"
DEFAULT_REVIEW = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_review_v3.csv"
DEFAULT_REPORT = ROOT_DIR / "data" / "exports" / "role_job_evidence_v3_validation_report.md"

TARGET_ROLES = [
    "AI Backend Developer",
    "Backend Developer",
    "Builder",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Frontend Developer",
]

VALIDATION_FIELDS = [
    "original_job_role_category",
    "validated_job_role_category",
    "evidence_status",
    "evidence_reason",
    "matched_required_signals",
    "matched_exclusion_signals",
    "manual_review_required",
]

AI_UNIQUE_SIGNALS = {
    "LLM": r"\bllms?\b|large language model",
    "RAG": r"\brag\b|retrieval[- ]augmented",
    "Retrieval": r"\bretrieval\b",
    "Embedding": r"\bembeddings?\b",
    "Vector Database": r"\bvector (database|db|store)\b|\bpgvector\b",
    "LangChain": r"\blangchain\b",
    "Generative AI": r"\bgenerative ai\b|\bgenai\b",
    "Inference Serving": r"\binference (serving|server|service)\b|\bserve inference\b",
    "Model Serving": r"\bmodel (serving|server|service)\b|\bserve models?\b",
}

AI_SERVICE_SIGNALS = {
    "Backend": r"\bback[- ]?end\b",
    "API": r"\bapi(s)?\b",
    "FastAPI": r"\bfastapi\b",
    "Service": r"\bservices?\b|\bservice-oriented\b",
    "Platform": r"\bplatform\b",
    "Deployment": r"\bdeploy(ment|ed|ing)?\b",
    "Docker": r"\bdocker\b|\bcontainers?\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "PostgreSQL": r"\bpostgres(ql)?\b",
}

ML_MODEL_SIGNALS = {
    "Fraud Prediction": r"\bfraud (prediction|detection|model)",
    "Recommendation Model": r"\b(recommendation|recommender) (model|system)",
    "Personalization Model": r"\bpersonalization (model|system)",
    "Classification": r"\bclassification\b|\bclassifier\b",
    "Regression": r"\bregression\b",
    "Feature Engineering": r"\bfeature engineering\b|\bfeature pipeline",
    "Model Training": r"\bmodel training\b|\btrain(ing)? (ml |machine learning )?models?\b",
    "Deep Learning": r"\bdeep learning\b",
    "PyTorch": r"\bpytorch\b",
    "TensorFlow": r"\btensorflow\b",
    "Experimentation": r"\bexperimentation\b|\ba/?b test",
}

AI_AMBIGUOUS_TITLE_SIGNALS = {
    "Machine Learning Engineer Title": r"\bmachine learning engineer\b|\bml engineer\b",
    "ML Infrastructure Title": r"\bml infrastructure\b|\bmachine learning infrastructure\b",
    "ML Platform Title": r"\bml platform\b|\bmachine learning platform\b",
    "Research Engineer Title": r"\bresearch engineer\b|\bresearcher\b",
    "Forward Deployed/Agent Builder Title": r"\bforward deployed\b|\bfde\b|\bagent builder\b",
}

BACKEND_REQUIRED = {
    "Backend": r"\bback[- ]?end\b",
    "API": r"\bapi(s)?\b",
    "Server": r"\bserver\b|\bserver-side\b",
    "Microservice": r"\bmicroservices?\b",
    "Distributed System": r"\bdistributed systems?\b",
    "Service Architecture": r"\bservice architecture\b|\bservice-oriented\b",
    "Database": r"\bdatabases?\b|\bpostgres(ql)?\b|\bmysql\b|\bredis\b",
}

BACKEND_EXCLUSION = {
    "Datacenter Hardware": r"\bdata ?center\b|\bdatacenter\b|\bserver lifecycle\b|\bhardware\b",
    "Audiovisual Infrastructure": r"\baudiovisual\b|\baudio visual\b|\bav infrastructure\b",
    "ML Platform": r"\bml platform\b|\bmachine learning platform\b|\bml infrastructure\b",
    "Frontend Focus": r"\bfront[- ]?end\b|\bfrontend\b|\bui engineer\b",
}

BUILDER_CORE = {
    "Product Engineer": r"\bproduct engineer\b",
    "Founding Engineer": r"\bfounding (software )?engineer\b",
    "Prototype": r"\bprototyp(e|ing)\b",
    "MVP": r"\bmvp\b|minimum viable product",
    "AI Application": r"\bai application\b|\bgenerative ai\b|\bllm\b|\brag\b",
    "Automation": r"\bautomation\b|\bautomate\b",
    "Integration": r"\bintegrations?\b",
    "End-to-End Product Build": r"\bend[- ]to[- ]end\b.*\b(product|build|application)\b",
}

BUILDER_FULL_STACK = {
    "Full Stack": r"\bfull[- ]?stack\b|\bfullstack\b",
}

BUILDER_TITLE_EXCLUSION = {
    "Sales Engineer": r"\bsales engineer\b",
    "Solutions Engineer": r"\bsolutions? engineer\b",
    "Professional Services": r"\bprofessional services\b",
}

BUILDER_CONTEXT_EXCLUSION = {
    "Pre-sales": r"\bpre[- ]?sales\b",
    "Enterprise Deal": r"\benterprise deal\b|\bdeal cycle\b",
    "Account Executive Collaboration": r"\baccount executives?\b",
}

ANALYST_REQUIRED = {
    "Data Analyst": r"\bdata analyst\b",
    "SQL": r"\bsql\b",
    "Analytics": r"\banalytics?\b",
    "Dashboard": r"\bdashboards?\b",
    "Reporting": r"\breporting\b|\breports?\b",
    "BI": r"\bbusiness intelligence\b|\bbi\b",
    "Metrics": r"\bmetrics?\b|\bkpis?\b",
    "Product Analytics": r"\bproduct analytics\b",
    "Business Insight": r"\bbusiness insights?\b",
}

ANALYST_EXCLUSION = {
    "ML Engineering": r"\bmachine learning engineer\b|\bml engineer\b|\bml platform\b",
    "Model Training": r"\bmodel training\b|\btraining models?\b",
    "Research": r"\bresearch (scientist|engineer)\b",
}

DATA_ENGINEER_REQUIRED = {
    "Data Engineer": r"\bdata engineer\b|\bdata engineering\b",
    "Data Pipeline": r"\bdata pipelines?\b|\bpipelines?\b",
    "ETL": r"\betl\b|\belt\b",
    "Warehouse": r"\bwarehouse\b|\bdata warehouse\b|\bdbt\b",
    "Data Platform": r"\bdata platform\b",
    "Airflow": r"\bairflow\b",
    "Spark": r"\bspark\b",
    "Kafka": r"\bkafka\b",
    "Batch/Streaming": r"\bbatch\b|\bstreaming\b",
}

DATA_ENGINEER_EXCLUSION = {
    "General Backend": r"\bbackend engineer\b|\bback-end engineer\b",
    "AI Platform": r"\bai platform\b|\bml platform\b|\bmachine learning platform\b",
    "Analytics Only": r"\bdata analyst\b|\bbusiness analyst\b|\breporting analyst\b",
}

DATA_SCIENTIST_REQUIRED = {
    "Data Scientist": r"\bdata scientist\b|\bscientist\b",
    "Statistical Analysis": r"\bstatistical\b|\bstatistics\b",
    "Experimentation": r"\bexperimentation\b|\ba/?b test",
    "Prediction": r"\bprediction\b|\bpredictive\b",
    "Classification": r"\bclassification\b|\bclassifier\b",
    "Regression": r"\bregression\b",
    "Model Evaluation": r"\bmodel evaluation\b|\bevaluate models?\b",
    "Insight": r"\binsights?\b",
}

DATA_SCIENTIST_EXCLUSION = {
    "LLM Product Service": r"\bllm\b.*\b(service|application|product|api)\b|\brag\b",
    "Backend/API Platform": r"\bbackend\b|\bapi platform\b|\bservice platform\b",
    "ML Infrastructure": r"\bml infrastructure\b|\bmachine learning infrastructure\b|\bmodel serving\b",
}

FRONTEND_REQUIRED = {
    "Frontend": r"\bfront[- ]?end\b|\bfrontend\b",
    "UI": r"\bui\b|\buser interface\b",
    "Web Client": r"\bweb client\b|\bclient-side\b",
    "React": r"\breact\b",
    "TypeScript": r"\btypescript\b",
    "JavaScript": r"\bjavascript\b",
    "Component": r"\bcomponents?\b",
    "Design System": r"\bdesign systems?\b",
}

FRONTEND_EXCLUSION = {
    "Full Stack Weak Frontend": r"\bfull[- ]?stack\b|\bfullstack\b",
    "Backend": r"\bback[- ]?end\b|\bbackend\b",
    "Infrastructure": r"\binfrastructure\b|\bplatform engineer\b",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build role evidence v3 CSVs using conservative role-specific validation rules."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--accepted-output", type=Path, default=DEFAULT_ACCEPTED)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    input_path = args.input.resolve()
    rows, original_fields = read_csv(input_path)
    assessed = [assess_row(row) for row in rows]
    accepted = [row for row in assessed if row["evidence_status"] == "accepted"]
    not_accepted = [row for row in assessed if row["evidence_status"] != "accepted"]

    output_fields = original_fields + VALIDATION_FIELDS
    write_csv(args.accepted_output.resolve(), output_fields, accepted)
    write_csv(args.review_output.resolve(), output_fields, not_accepted)
    write_report(
        path=args.report_output.resolve(),
        input_path=input_path,
        assessed=assessed,
        accepted=accepted,
    )
    print_summary(
        input_path=input_path,
        accepted_path=args.accepted_output.resolve(),
        review_path=args.review_output.resolve(),
        report_path=args.report_output.resolve(),
        assessed=assessed,
    )


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), list(reader.fieldnames or [])


def assess_row(row: dict[str, str]) -> dict[str, str]:
    original_role = value(row, "job_role_category")
    assessor = {
        "AI Backend Developer": assess_ai_backend,
        "Backend Developer": assess_backend,
        "Builder": assess_builder,
        "Data Analyst": assess_data_analyst,
        "Data Engineer": assess_data_engineer,
        "Data Scientist": assess_data_scientist,
        "Frontend Developer": assess_frontend,
    }.get(original_role)
    if not assessor:
        result = decision("review", "Unknown target role; manual review required.", [], [])
    else:
        result = assessor(row)
    validated_role = original_role if result["status"] == "accepted" else ""
    return {
        **row,
        "original_job_role_category": original_role,
        "validated_job_role_category": validated_role,
        "evidence_status": result["status"],
        "evidence_reason": result["reason"],
        "matched_required_signals": "; ".join(result["required"]),
        "matched_exclusion_signals": "; ".join(result["excluded"]),
        "manual_review_required": "true" if result["status"] == "review" else "false",
    }


def assess_ai_backend(row: dict[str, str]) -> dict:
    text = evidence_text(row)
    unique_hits = match_signals(text, AI_UNIQUE_SIGNALS)
    service_hits = match_signals(text, AI_SERVICE_SIGNALS)
    model_hits = match_signals(text, ML_MODEL_SIGNALS)
    ambiguous_title_hits = match_signals(value(row, "title"), AI_AMBIGUOUS_TITLE_SIGNALS)
    required = prefixed("ai", unique_hits) + prefixed("service", service_hits)
    excluded = prefixed("ml_model", model_hits) + prefixed("boundary_title", ambiguous_title_hits)
    if unique_hits and service_hits and len(model_hits) >= 2:
        return decision(
            "review",
            "AI service signals are present, but strong ML-model signals require boundary review.",
            required,
            excluded,
        )
    if unique_hits and service_hits and ambiguous_title_hits:
        return decision(
            "review",
            "AI service signals exist, but the title overlaps with an ML, research, or builder boundary role.",
            required,
            excluded,
        )
    if unique_hits and service_hits:
        return decision(
            "accepted",
            "Contains both AI-specific and service implementation signals.",
            required,
            excluded,
        )
    if len(model_hits) >= 2 and not service_hits:
        return decision(
            "excluded",
            "Strong ML-model focus without service implementation evidence.",
            required,
            excluded,
        )
    if unique_hits or service_hits or model_hits:
        return decision(
            "review",
            "Some AI/backend/model evidence exists, but AI service responsibility is not clear.",
            required,
            excluded,
        )
    return decision(
        "excluded",
        "No AI-specific or service implementation evidence found.",
        required,
        excluded,
    )


def assess_backend(row: dict[str, str]) -> dict:
    text = evidence_text(row)
    required = match_signals(text, BACKEND_REQUIRED)
    excluded = match_signals(text, BACKEND_EXCLUSION)
    if excluded and not required:
        return decision(
            "excluded",
            "Infrastructure/frontend/ML-platform context without backend role evidence.",
            required,
            excluded,
        )
    if excluded:
        return decision(
            "review",
            "Backend signals coexist with competing infrastructure or platform context.",
            required,
            excluded,
        )
    if required:
        return decision("accepted", "Clear backend service or server-side context.", required, excluded)
    return decision("review", "Backend role context is not explicit enough.", required, excluded)


def assess_builder(row: dict[str, str]) -> dict:
    text = evidence_text(row)
    core_hits = match_signals(text, BUILDER_CORE)
    full_stack_hits = match_signals(text, BUILDER_FULL_STACK)
    excluded = match_signals(value(row, "title"), BUILDER_TITLE_EXCLUSION) + match_signals(
        text, BUILDER_CONTEXT_EXCLUSION
    )
    required = core_hits + full_stack_hits
    if excluded:
        return decision(
            "excluded",
            "Solutions/sales/professional-services context is outside the product-builder target.",
            required,
            excluded,
        )
    if core_hits:
        return decision(
            "accepted",
            "Contains product delivery, AI application, MVP, automation, or integration context.",
            required,
            excluded,
        )
    if full_stack_hits:
        return decision(
            "review",
            "General full-stack role without clear AI/MVP/product-building evidence.",
            required,
            excluded,
        )
    return decision("review", "Builder-specific product creation context is unclear.", required, excluded)


def assess_data_analyst(row: dict[str, str]) -> dict:
    text = evidence_text(row)
    required = match_signals(text, ANALYST_REQUIRED)
    excluded = match_signals(text, ANALYST_EXCLUSION)
    if excluded and not required:
        return decision("excluded", "ML engineering or research focus without analyst context.", required, excluded)
    if excluded:
        return decision("review", "Analytics context overlaps with ML engineering or research.", required, excluded)
    if required:
        return decision("accepted", "Clear analytics, reporting, BI, metrics, or SQL context.", required, excluded)
    return decision("review", "Analyst evidence is not explicit enough.", required, excluded)


def assess_data_engineer(row: dict[str, str]) -> dict:
    text = evidence_text(row)
    required = match_signals(text, DATA_ENGINEER_REQUIRED)
    excluded = match_signals(text, DATA_ENGINEER_EXCLUSION)
    if excluded and not required:
        return decision("excluded", "Competing backend, AI platform, or analyst context only.", required, excluded)
    if excluded:
        return decision("review", "Data engineering evidence overlaps with competing role context.", required, excluded)
    if required:
        return decision("accepted", "Clear pipeline, warehouse, platform, or data-processing context.", required, excluded)
    return decision("review", "Data engineering responsibility is not explicit enough.", required, excluded)


def assess_data_scientist(row: dict[str, str]) -> dict:
    text = evidence_text(row)
    required = match_signals(text, DATA_SCIENTIST_REQUIRED)
    excluded = match_signals(text, DATA_SCIENTIST_EXCLUSION)
    if excluded and not required:
        return decision("excluded", "Service/platform/infrastructure focus without data-science evidence.", required, excluded)
    if excluded:
        return decision("review", "Data-science evidence overlaps with product service or infrastructure.", required, excluded)
    if required:
        return decision("accepted", "Clear analysis, experimentation, modeling, evaluation, or insight context.", required, excluded)
    return decision("review", "Data-science responsibility is not explicit enough.", required, excluded)


def assess_frontend(row: dict[str, str]) -> dict:
    text = evidence_text(row)
    required = match_signals(text, FRONTEND_REQUIRED)
    excluded = match_signals(text, FRONTEND_EXCLUSION)
    frontend_identity = bool(match_signals(value(row, "title"), {"Frontend": FRONTEND_REQUIRED["Frontend"]}))
    if excluded and not required:
        return decision("excluded", "Backend/infrastructure/full-stack context without frontend evidence.", required, excluded)
    if excluded and not frontend_identity:
        return decision("review", "Frontend technologies exist but the role context is mixed.", required, excluded)
    if required:
        return decision("accepted", "Clear frontend, UI, web-client, or component context.", required, excluded)
    return decision("review", "Frontend responsibility is not explicit enough.", required, excluded)


def decision(status: str, reason: str, required: list[str], excluded: list[str]) -> dict:
    return {
        "status": status,
        "reason": reason,
        "required": required,
        "excluded": excluded,
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    input_path: Path,
    assessed: list[dict[str, str]],
    accepted: list[dict[str, str]],
) -> None:
    original_by_role = group_by_role(assessed)
    accepted_by_role = group_by_role(accepted)
    status_counts = counts_by_status(assessed)
    original_skills = {role: top_skills(original_by_role.get(role, [])) for role in TARGET_ROLES}
    accepted_skills = {role: top_skills(accepted_by_role.get(role, [])) for role in TARGET_ROLES}
    repeated_titles = repeated_company_titles(accepted)
    lines = [
        "# Role Job Evidence Candidate Dataset v3 Validation Report",
        "",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Input CSV: `{input_path.as_posix()}`",
        f"- Input rows: {len(assessed):,}",
        f"- Accepted rows: {len(accepted):,}",
        "- Safety: File generation only. No database write, embedding generation, or OpenAI API call was executed.",
        "- Label policy: Records are not automatically moved to another role. Only accepted records retain a validated role label.",
        "",
        "## Classification Rules",
        "",
        "- AI Backend Developer is accepted only when at least one AI-specific signal and at least one service implementation signal are both present. Strong ML-model overlap is routed to review.",
        "- Backend Developer requires server-side/service/database context; hardware, audiovisual, ML-platform, or frontend overlap is held back.",
        "- Builder means AI/MVP/product-building delivery, not generic solutions or sales engineering. Generic full-stack evidence alone is reviewed.",
        "- Data Analyst, Data Engineer, Data Scientist, and Frontend Developer require their explicit role contexts and hold competing role signals for review or exclusion.",
        "",
        "## Status by Role",
        "",
        "| Role | Original | Accepted | Accepted % | Review | Review % | Excluded | Excluded % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for role in TARGET_ROLES:
        original = len(original_by_role.get(role, []))
        counts = status_counts[role]
        lines.append(
            f"| {role} | {original:,} | {counts['accepted']:,} | {pct(counts['accepted'], original):.1f}% | "
            f"{counts['review']:,} | {pct(counts['review'], original):.1f}% | "
            f"{counts['excluded']:,} | {pct(counts['excluded'], original):.1f}% |"
        )
    total_counts = Counter(row["evidence_status"] for row in assessed)
    lines.append(
        f"| **Total** | **{len(assessed):,}** | **{total_counts['accepted']:,}** | "
        f"**{pct(total_counts['accepted'], len(assessed)):.1f}%** | **{total_counts['review']:,}** | "
        f"**{pct(total_counts['review'], len(assessed)):.1f}%** | **{total_counts['excluded']:,}** | "
        f"**{pct(total_counts['excluded'], len(assessed)):.1f}%** |"
    )
    lines.extend(
        [
            "",
            "## Repeated Company/Title Check in Accepted Candidates",
            "",
            "- Repeated company/title rows are retained because distinct posting IDs or URLs can represent separate openings. Review this before production embedding if repeated wording should not amplify evidence.",
            "",
            "| Role | Repeated Company/Title Groups | Extra Rows Beyond One per Group |",
            "|---|---:|---:|",
        ]
    )
    for role in TARGET_ROLES:
        groups, extra_rows = repeated_titles[role]
        lines.append(f"| {role} | {groups:,} | {extra_rows:,} |")

    lines.extend(["", "## Accepted Top 20 Skills and Change from v2", ""])
    for role in TARGET_ROLES:
        lines.extend(
            [
                f"### {role}",
                "",
                f"- Original documents: {len(original_by_role.get(role, [])):,}; accepted documents: {len(accepted_by_role.get(role, [])):,}",
                "",
                "| Rank | Skill | Original Count / Share | Accepted Count / Share | Share Change |",
                "|---:|---|---:|---:|---:|",
            ]
        )
        original_map = {skill: (count, ratio) for skill, count, ratio in original_skills[role]}
        for rank, (skill, count, ratio) in enumerate(accepted_skills[role], start=1):
            old_count, old_ratio = original_map.get(skill, (0, 0.0))
            lines.append(
                f"| {rank} | {md(skill)} | {old_count:,} / {old_ratio:.1f}% | "
                f"{count:,} / {ratio:.1f}% | {ratio - old_ratio:+.1f} pp |"
            )
        if not accepted_skills[role]:
            lines.append("| - | No accepted documents | - | - | - |")
        lines.append("")

    lines.extend(["## Status Samples by Role", ""])
    for role in TARGET_ROLES:
        lines.extend([f"### {role}", ""])
        role_rows = original_by_role.get(role, [])
        for status in ["accepted", "review", "excluded"]:
            lines.extend([f"#### {status.title()}", ""])
            samples = select_samples(role_rows, status, 5)
            if not samples:
                lines.extend(["- No records in this status.", ""])
            for index, row in enumerate(samples, start=1):
                lines.extend(sample_markdown(index, row))

    lines.extend(["## AI Backend Developer Detailed Decision Review", ""])
    ai_rows = original_by_role.get("AI Backend Developer", [])
    ai_counts = status_counts["AI Backend Developer"]
    lines.extend(
        [
            "| Status | Documents | Share |",
            "|---|---:|---:|",
            f"| Accepted | {ai_counts['accepted']:,} | {pct(ai_counts['accepted'], len(ai_rows)):.1f}% |",
            f"| Review | {ai_counts['review']:,} | {pct(ai_counts['review'], len(ai_rows)):.1f}% |",
            f"| Excluded | {ai_counts['excluded']:,} | {pct(ai_counts['excluded'], len(ai_rows)):.1f}% |",
            "",
            "### Decision Reasons",
            "",
            "| Status | Reason | Documents |",
            "|---|---|---:|",
        ]
    )
    for (status, reason), count in Counter(
        (row["evidence_status"], row["evidence_reason"]) for row in ai_rows
    ).most_common():
        lines.append(f"| {status} | {md(reason)} | {count:,} |")
    lines.append("")

    builder_rows = original_by_role.get("Builder", [])
    solutions_rows = [
        row for row in builder_rows if re.search(r"\bsolutions? engineer\b", value(row, "title"), re.IGNORECASE)
    ]
    solutions_status = Counter(row["evidence_status"] for row in solutions_rows)
    lines.extend(
        [
            "## Builder Solutions Engineer Review",
            "",
            f"- Builder original rows: {len(builder_rows):,}",
            f"- Rows matching `Solutions Engineer`: {len(solutions_rows):,}",
            f"- Accepted: {solutions_status['accepted']:,}",
            f"- Review: {solutions_status['review']:,}",
            f"- Excluded: {solutions_status['excluded']:,}",
            "",
        ]
    )

    lines.extend(
        [
            "## Final Recommendation",
            "",
            "- The full v2 dataset must not be indexed as RAG evidence without filtering.",
            "- The accepted v3 dataset is a safer candidate for RAG document generation because ambiguous and conflicting records have been separated.",
            "- Review rows should be manually checked before any attempt to expand coverage, especially AI Backend, Backend infrastructure boundaries, and Builder solutions/full-stack roles.",
            "- JobRoleSkillEvidence should be recalculated from the same accepted v3 population before its scores are presented together with RAG evidence cards.",
            "- No embedding should be executed until this accepted/review split is approved.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(
    input_path: Path,
    accepted_path: Path,
    review_path: Path,
    report_path: Path,
    assessed: list[dict[str, str]],
) -> None:
    status_counts = counts_by_status(assessed)
    print("Role evidence candidate v3 built from CSV only (no DB write; no OpenAI call).")
    print(f"Input: {input_path}")
    print(f"Accepted CSV: {accepted_path}")
    print(f"Review/excluded CSV: {review_path}")
    print(f"Validation report: {report_path}")
    for role in TARGET_ROLES:
        counts = status_counts[role]
        total = sum(counts.values())
        print(
            f"{role}: original={total}, accepted={counts['accepted']}, "
            f"review={counts['review']}, excluded={counts['excluded']}"
        )
    builder_solutions = [
        row
        for row in assessed
        if value(row, "original_job_role_category") == "Builder"
        and re.search(r"\bsolutions? engineer\b", value(row, "title"), re.IGNORECASE)
    ]
    status = Counter(row["evidence_status"] for row in builder_solutions)
    print(
        "Builder Solutions Engineer: "
        f"total={len(builder_solutions)}, accepted={status['accepted']}, "
        f"review={status['review']}, excluded={status['excluded']}"
    )


def top_skills(rows: list[dict[str, str]]) -> list[tuple[str, int, float]]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(set(parse_skills(value(row, "final_skills"))))
    return [(skill, count, pct(count, len(rows))) for skill, count in counts.most_common(20)]


def counts_by_status(rows: list[dict[str, str]]) -> dict[str, Counter]:
    output = {role: Counter({"accepted": 0, "review": 0, "excluded": 0}) for role in TARGET_ROLES}
    for row in rows:
        output[value(row, "original_job_role_category")][row["evidence_status"]] += 1
    return output


def group_by_role(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[value(row, "original_job_role_category")].append(row)
    return grouped


def repeated_company_titles(rows: list[dict[str, str]]) -> dict[str, tuple[int, int]]:
    output = {}
    for role in TARGET_ROLES:
        counts = Counter(
            (value(row, "company").lower(), value(row, "title").lower())
            for row in rows
            if value(row, "original_job_role_category") == role
        )
        repeated = [count for count in counts.values() if count > 1]
        output[role] = (len(repeated), sum(count - 1 for count in repeated))
    return output


def select_samples(rows: list[dict[str, str]], status: str, count: int) -> list[dict[str, str]]:
    candidates = [row for row in rows if row["evidence_status"] == status]
    sorted_candidates = sorted(
        candidates,
        key=lambda row: (
            -len(value(row, "matched_required_signals").split("; ")),
            -len(value(row, "matched_exclusion_signals").split("; ")),
            value(row, "company"),
            value(row, "title"),
        ),
    )
    selected = []
    seen_company_titles: set[tuple[str, str]] = set()
    for row in sorted_candidates:
        identity = (value(row, "company").lower(), value(row, "title").lower())
        if identity in seen_company_titles:
            continue
        seen_company_titles.add(identity)
        selected.append(row)
        if len(selected) >= count:
            break
    return selected


def sample_markdown(index: int, row: dict[str, str]) -> list[str]:
    return [
        f"{index}. **{md(value(row, 'company'))} - {md(value(row, 'title'))}**",
        f"   - Skills: {md(value(row, 'final_skills'))}",
        f"   - Required signals: {md(value(row, 'matched_required_signals') or 'none')}",
        f"   - Exclusion signals: {md(value(row, 'matched_exclusion_signals') or 'none')}",
        f"   - Reason: {md(value(row, 'evidence_reason'))}",
        f"   - URL: {md(value(row, 'job_url'))}",
        "",
    ]


def evidence_text(row: dict[str, str]) -> str:
    return " ".join(
        value(row, field)
        for field in [
            "title",
            "responsibilities",
            "requirements",
            "preferred_qualifications",
            "final_skills",
        ]
    )


def match_signals(text: str, signals: dict[str, str]) -> list[str]:
    return [
        name for name, pattern in signals.items() if re.search(pattern, text, flags=re.IGNORECASE)
    ]


def prefixed(prefix: str, values: list[str]) -> list[str]:
    return [f"{prefix}:{signal}" for signal in values]


def parse_skills(text: str) -> list[str]:
    return [skill.strip() for skill in text.split(";") if skill.strip()]


def pct(count: int, total: int) -> float:
    return count / total * 100 if total else 0.0


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def md(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
