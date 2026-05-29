import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_analysis_ml_skills_v2.csv"
DEFAULT_REPORT = ROOT_DIR / "data" / "exports" / "role_job_evidence_validation_report.md"
DEFAULT_SAMPLES = ROOT_DIR / "data" / "exports" / "role_job_evidence_validation_samples.csv"

TARGET_ROLES = [
    "AI Backend Developer",
    "Backend Developer",
    "Builder",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Frontend Developer",
]

AI_BACKEND_SIGNALS = {
    "FastAPI": r"\bfastapi\b",
    "API": r"\bapi(s)?\b",
    "Backend": r"\bback[- ]?end\b",
    "LLM": r"\bllm(s)?\b|large language model",
    "RAG": r"\brag\b|retrieval[- ]augmented",
    "Retrieval": r"\bretrieval\b",
    "Embedding": r"\bembedding(s)?\b",
    "Vector Database": r"\bvector (database|db|store)\b|\bpgvector\b",
    "PostgreSQL": r"\bpostgres(ql)?\b",
    "Docker": r"\bdocker\b|containeri[sz]",
    "LangChain": r"\blangchain\b",
    "Inference Serving": r"\binference (serving|server|service)\b|\bserve inference\b",
    "Model Serving": r"\bmodel (serving|server|service)\b|\bserve models?\b",
}

ML_MODEL_SIGNALS = {
    "Fraud Prediction": r"\bfraud (prediction|detection|model)",
    "Recommendation Model": r"\b(recommendation|recommender) (model|system)",
    "PyTorch": r"\bpytorch\b",
    "TensorFlow": r"\btensorflow\b",
    "Deep Learning": r"\bdeep learning\b",
    "Feature Engineering": r"\bfeature engineering\b|\bfeature pipeline",
    "Model Training": r"\bmodel training\b|\btrain(ing)? (ml |machine learning )?models?\b",
    "Classification": r"\bclassification\b|\bclassifier\b",
    "Regression": r"\bregression\b",
    "Experimentation": r"\bexperimentation\b|\ba/?b test",
}

BOUNDARY_SIGNALS = {
    "AI Backend Developer": {
        "LLM/RAG": r"\b(llm|rag|retrieval|embedding|langchain|generative ai)\b",
        "Inference": r"\binference\b|\bmodel serving\b",
    },
    "Backend Developer": {
        "Backend/API": r"\b(back[- ]?end|api|server|microservice)\b",
        "Distributed Systems": r"\bdistributed systems?\b",
    },
    "Builder": {
        "Full Stack": r"\bfull[- ]?stack\b|\bfullstack\b",
        "Product": r"\bproduct engineer\b|\bfounding engineer\b",
        "Solutions": r"\bsolutions? engineer\b|\bimplementation engineer\b",
    },
    "Data Analyst": {
        "Analytics": r"\banalytics?\b|\bbusiness intelligence\b|\bbi\b",
        "Reporting": r"\bdashboard\b|\breporting\b",
    },
    "Data Engineer": {
        "Pipeline/ETL": r"\bdata pipeline\b|\betl\b|\bdata platform\b",
        "Warehouse": r"\bwarehouse\b|\bdbt\b|\bairflow\b",
    },
    "Data Scientist": {
        "Scientist": r"\bscientist\b|\bresearch\b",
        "Modeling": r"\bprediction\b|\bmodel training\b|\bclassification\b|\bregression\b",
        "Experiments": r"\bexperimentation\b|\bstatistical\b",
    },
    "Frontend Developer": {
        "Frontend/UI": r"\bfront[- ]?end\b|\bfrontend\b|\bui\b",
        "Web Client": r"\breact\b|\btypescript\b|\bjavascript\b",
    },
}

TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "contract",
    "developer",
    "engineer",
    "engineering",
    "i",
    "ii",
    "iii",
    "lead",
    "manager",
    "of",
    "principal",
    "remote",
    "senior",
    "staff",
    "the",
}

PAIR_COMPARISONS = [
    ("AI Backend Developer", "Data Scientist"),
    ("AI Backend Developer", "Data Engineer"),
    ("Backend Developer", "AI Backend Developer"),
    ("Builder", "AI Backend Developer"),
    ("Builder", "Backend Developer"),
    ("Builder", "Frontend Developer"),
]

SAMPLE_FIELDS = [
    "sample_group",
    "sample_type",
    "job_role_category",
    "source_posting_id",
    "company",
    "title",
    "final_skills",
    "excerpt",
    "job_url",
    "ai_backend_signals",
    "ml_model_signals",
    "boundary_role",
    "diagnostic_note",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate role evidence document quality without database writes or API calls."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--samples-output", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--samples-per-role", type=int, default=10)
    args = parser.parse_args()

    rows = read_csv(args.input.resolve())
    enriched_rows = [enrich_row(row) for row in rows]
    grouped = group_by_role(enriched_rows)
    top_skills = {role: skill_frequencies(grouped.get(role, [])) for role in TARGET_ROLES}
    role_samples = select_role_samples(grouped, top_skills, args.samples_per_role)
    ai_diagnostic = diagnose_ai_backend(grouped.get("AI Backend Developer", []))
    pair_diagnostics = compare_role_pairs(grouped, top_skills)
    conclusion = indexing_conclusion(ai_diagnostic)

    sample_rows = []
    for role in TARGET_ROLES:
        sample_rows.extend(role_samples.get(role, []))
    sample_rows.extend(ai_diagnostic["ml_only_samples"])

    write_samples_csv(args.samples_output.resolve(), sample_rows)
    write_markdown_report(
        path=args.report_output.resolve(),
        input_path=args.input.resolve(),
        rows=rows,
        grouped=grouped,
        top_skills=top_skills,
        role_samples=role_samples,
        ai_diagnostic=ai_diagnostic,
        pair_diagnostics=pair_diagnostics,
        conclusion=conclusion,
    )

    print_summary(
        input_path=args.input.resolve(),
        report_path=args.report_output.resolve(),
        samples_path=args.samples_output.resolve(),
        grouped=grouped,
        ai_diagnostic=ai_diagnostic,
        conclusion=conclusion,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def enrich_row(row: dict[str, str]) -> dict:
    text = diagnostic_text(row)
    ai_hits = match_signals(text, AI_BACKEND_SIGNALS)
    ml_hits = match_signals(text, ML_MODEL_SIGNALS)
    ai_strong = len(ai_hits) >= 2
    ml_strong = len(ml_hits) >= 2
    boundary_role, boundary_hits = strongest_boundary(row, text)
    return {
        **row,
        "_skills": parse_skills(value(row, "final_skills")),
        "_text": text,
        "_excerpt": excerpt(row),
        "_ai_hits": ai_hits,
        "_ml_hits": ml_hits,
        "_ai_strong": ai_strong,
        "_ml_strong": ml_strong,
        "_ml_only": ml_strong and not ai_strong,
        "_both": ml_strong and ai_strong,
        "_boundary_role": boundary_role,
        "_boundary_hits": boundary_hits,
    }


def group_by_role(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[value(row, "job_role_category")].append(row)
    return grouped


def skill_frequencies(rows: list[dict]) -> list[tuple[str, int, float]]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(set(row["_skills"]))
    denominator = len(rows)
    return [
        (skill, count, percentage(count, denominator))
        for skill, count in counts.most_common(20)
    ]


def select_role_samples(
    grouped: dict[str, list[dict]],
    top_skills: dict[str, list[tuple[str, int, float]]],
    sample_count: int,
) -> dict[str, list[dict]]:
    output: dict[str, list[dict]] = {}
    representative_count = max(1, sample_count // 2)
    for role in TARGET_ROLES:
        rows = grouped.get(role, [])
        weights = {skill: count for skill, count, _ in top_skills.get(role, [])[:10]}
        representatives = sorted(
            rows,
            key=lambda row: (
                -sum(weights.get(skill, 0) for skill in set(row["_skills"])),
                -len(row["_skills"]),
                value(row, "company"),
                value(row, "title"),
            ),
        )
        selected = unique_samples(
            representatives,
            representative_count,
            sample_group=f"{role} representative",
            sample_type="representative_top_skills",
        )
        used = {sample["source_posting_id"] for sample in selected}
        boundary_candidates = sorted(
            [row for row in rows if source_id(row) not in used],
            key=lambda row: (
                -boundary_priority(role, row),
                -len(row["_ml_hits"]),
                -len(row["_ai_hits"]),
                value(row, "company"),
                value(row, "title"),
            ),
        )
        selected.extend(
            unique_samples(
                boundary_candidates,
                max(0, sample_count - len(selected)),
                sample_group=f"{role} boundary",
                sample_type="boundary_review",
            )
        )
        output[role] = selected
    return output


def diagnose_ai_backend(rows: list[dict]) -> dict:
    total = len(rows)
    ai_strong = [row for row in rows if row["_ai_strong"]]
    ml_strong = [row for row in rows if row["_ml_strong"]]
    both = [row for row in rows if row["_both"]]
    ml_only = [row for row in rows if row["_ml_only"]]
    neither = [row for row in rows if not row["_ai_strong"] and not row["_ml_strong"]]
    ranked_ml_only = sorted(
        ml_only,
        key=lambda row: (
            -len(row["_ml_hits"]),
            len(row["_ai_hits"]),
            value(row, "company"),
            value(row, "title"),
        ),
    )
    samples = unique_samples(
        ranked_ml_only,
        20,
        sample_group="AI Backend Developer ML-only diagnostic",
        sample_type="ml_model_only_review",
    )
    return {
        "total": total,
        "ai_strong": (len(ai_strong), percentage(len(ai_strong), total)),
        "ml_strong": (len(ml_strong), percentage(len(ml_strong), total)),
        "both": (len(both), percentage(len(both), total)),
        "ml_only": (len(ml_only), percentage(len(ml_only), total)),
        "neither": (len(neither), percentage(len(neither), total)),
        "ml_only_samples": samples,
    }


def compare_role_pairs(
    grouped: dict[str, list[dict]],
    top_skills: dict[str, list[tuple[str, int, float]]],
) -> list[dict]:
    comparisons = []
    for first, second in PAIR_COMPARISONS:
        first_skill_map = {skill: (count, ratio) for skill, count, ratio in top_skills[first]}
        second_skill_map = {skill: (count, ratio) for skill, count, ratio in top_skills[second]}
        shared_skills = sorted(
            set(first_skill_map) & set(second_skill_map),
            key=lambda skill: (
                -min(first_skill_map[skill][1], second_skill_map[skill][1]),
                skill,
            ),
        )[:10]
        first_titles = title_token_counts(grouped.get(first, []))
        second_titles = title_token_counts(grouped.get(second, []))
        shared_title_terms = sorted(
            set(first_titles) & set(second_titles),
            key=lambda term: (-min(first_titles[term], second_titles[term]), term),
        )[:10]
        comparisons.append(
            {
                "roles": f"{first} vs {second}",
                "shared_skills": [
                    (
                        skill,
                        first_skill_map[skill][0],
                        first_skill_map[skill][1],
                        second_skill_map[skill][0],
                        second_skill_map[skill][1],
                    )
                    for skill in shared_skills
                ],
                "shared_title_terms": [
                    (term, first_titles[term], second_titles[term])
                    for term in shared_title_terms
                ],
                "risk": boundary_risk_summary(first, second, shared_skills, shared_title_terms),
            }
        )
    return comparisons


def indexing_conclusion(ai_diagnostic: dict) -> list[str]:
    ai_count, ai_ratio = ai_diagnostic["ai_strong"]
    ml_only_count, ml_only_ratio = ai_diagnostic["ml_only"]
    both_count, both_ratio = ai_diagnostic["both"]
    return [
        "현재 1,299건 전체를 그대로 임베딩하는 것은 권장하지 않습니다.",
        (
            "AI Backend Developer에서는 서비스/백엔드 근거가 강한 문서가 "
            f"{ai_count}건({ai_ratio:.1f}%)인 반면, ML Model 신호만 강한 문서가 "
            f"{ml_only_count}건({ml_only_ratio:.1f}%) 확인되었습니다."
        ),
        (
            "AI Backend 문서는 title 분류만 사용하지 말고, LLM/RAG/embedding/retrieval/"
            "inference serving/model serving/backend/API 등의 서비스 신호가 2개 이상인 "
            "문서를 우선 포함하며, ML Model 신호만 강한 문서는 Data Scientist 또는 "
            "별도 ML Engineer 검토 대상으로 분리하는 것이 적절합니다."
        ),
        (
            f"서비스와 모델 신호가 모두 강한 {both_count}건({both_ratio:.1f}%)은 "
            "AI 기능을 서비스화하는 역할일 수 있으므로 수동 검토 또는 복수 태그 후보입니다."
        ),
        (
            "JobRoleSkillEvidence가 현재 분류 라벨 전체를 기반으로 집계되어 있다면, "
            "AI Backend에 모델링 중심 공고가 포함된 상태에서 문서만 필터링할 경우 "
            "추천 스킬 점수와 제시 문서 근거가 어긋날 위험이 있습니다. "
            "최종 인덱싱 전에 동일 필터 기준으로 증거 집계도 재산출할지 결정해야 합니다."
        ),
    ]


def write_markdown_report(
    path: Path,
    input_path: Path,
    rows: list[dict[str, str]],
    grouped: dict[str, list[dict]],
    top_skills: dict[str, list[tuple[str, int, float]]],
    role_samples: dict[str, list[dict]],
    ai_diagnostic: dict,
    pair_diagnostics: list[dict],
    conclusion: list[str],
) -> None:
    lines = [
        "# Role Job Evidence RAG Validation Report",
        "",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Input CSV: `{input_path.as_posix()}`",
        f"- Total rows: {len(rows):,}",
        "- Safety: This validation reads the CSV only. It does not write to the database or call OpenAI.",
        "",
        "## Role Counts",
        "",
        "| Role | Documents |",
        "|---|---:|",
    ]
    for role in TARGET_ROLES:
        lines.append(f"| {role} | {len(grouped.get(role, [])):,} |")

    lines.extend(["", "## A. Top 20 Skills by Role", ""])
    for role in TARGET_ROLES:
        lines.extend(
            [
                f"### {role}",
                "",
                "| Rank | Skill | Documents | Share of Role |",
                "|---:|---|---:|---:|",
            ]
        )
        for rank, (skill, count, ratio) in enumerate(top_skills.get(role, []), start=1):
            lines.append(f"| {rank} | {md(skill)} | {count:,} | {ratio:.1f}% |")
        lines.append("")

    lines.extend(["## B. Representative and Boundary Samples", ""])
    for role in TARGET_ROLES:
        lines.extend([f"### {role}", ""])
        for index, sample in enumerate(role_samples.get(role, []), start=1):
            lines.extend(markdown_sample(index, sample))

    lines.extend(
        [
            "## C. AI Backend Developer Quality Check",
            "",
            "Diagnostic rules:",
            "",
            "- `AI Backend / LLM Service strong`: at least 2 distinct service signals among API, Backend, LLM, RAG, Retrieval, Embedding, vector DB, PostgreSQL, Docker, LangChain, inference serving and model serving.",
            "- `ML Model / Data Science strong`: at least 2 distinct modeling signals among fraud prediction, recommendation model, PyTorch, TensorFlow, Deep Learning, feature engineering, model training, classification, regression and experimentation.",
            "",
            "| Classification | Documents | Share |",
            "|---|---:|---:|",
            f"| AI Backend / LLM Service strong | {ai_diagnostic['ai_strong'][0]:,} | {ai_diagnostic['ai_strong'][1]:.1f}% |",
            f"| ML Model / Data Science strong | {ai_diagnostic['ml_strong'][0]:,} | {ai_diagnostic['ml_strong'][1]:.1f}% |",
            f"| Both strong | {ai_diagnostic['both'][0]:,} | {ai_diagnostic['both'][1]:.1f}% |",
            f"| ML Model strong only | {ai_diagnostic['ml_only'][0]:,} | {ai_diagnostic['ml_only'][1]:.1f}% |",
            f"| Neither strong | {ai_diagnostic['neither'][0]:,} | {ai_diagnostic['neither'][1]:.1f}% |",
            "",
            "### ML Model Strong Only Samples",
            "",
        ]
    )
    for index, sample in enumerate(ai_diagnostic["ml_only_samples"], start=1):
        lines.extend(markdown_sample(index, sample))

    lines.extend(["## D. Cross-Role Boundary Risk", ""])
    for comparison in pair_diagnostics:
        lines.extend([f"### {comparison['roles']}", "", f"- Summary: {comparison['risk']}", ""])
        lines.extend(
            [
                "| Shared top skill | First role | Second role |",
                "|---|---:|---:|",
            ]
        )
        for skill, first_count, first_ratio, second_count, second_ratio in comparison["shared_skills"]:
            lines.append(
                f"| {md(skill)} | {first_count:,} ({first_ratio:.1f}%) | "
                f"{second_count:,} ({second_ratio:.1f}%) |"
            )
        lines.extend(["", "| Shared title term | First role titles | Second role titles |", "|---|---:|---:|"])
        for term, first_count, second_count in comparison["shared_title_terms"]:
            lines.append(f"| {md(term)} | {first_count:,} | {second_count:,} |")
        lines.append("")

    lines.extend(["## E. RAG Indexing Recommendation", ""])
    lines.extend(f"- {item}" for item in conclusion)
    lines.extend(
        [
            "",
            "## Next Gate Before Embedding",
            "",
            "1. Decide whether to exclude or relabel AI Backend `ML Model strong only` documents.",
            "2. Review the sample CSV for borderline cases in other role pairs.",
            "3. If filters change document membership, rebuild `JobRoleSkillEvidence` from the same accepted set before connecting recommendation evidence.",
            "4. Only after approval, run the separate indexing/embedding command.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_samples_csv(path: Path, samples: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SAMPLE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(samples)


def print_summary(
    input_path: Path,
    report_path: Path,
    samples_path: Path,
    grouped: dict[str, list[dict]],
    ai_diagnostic: dict,
    conclusion: list[str],
) -> None:
    print("Role job evidence validation completed (CSV read only; no DB write; no OpenAI call).")
    print(f"Input: {input_path}")
    print(f"Markdown report: {report_path}")
    print(f"Samples CSV: {samples_path}")
    print("Role counts:")
    for role in TARGET_ROLES:
        print(f"  - {role}: {len(grouped.get(role, []))}")
    print("AI Backend Developer diagnostic:")
    print(
        f"  - AI Backend / LLM Service strong: {ai_diagnostic['ai_strong'][0]} "
        f"({ai_diagnostic['ai_strong'][1]:.1f}%)"
    )
    print(
        f"  - ML Model strong only: {ai_diagnostic['ml_only'][0]} "
        f"({ai_diagnostic['ml_only'][1]:.1f}%)"
    )
    print(f"Recommendation: {conclusion[0]}")


def markdown_sample(index: int, sample: dict) -> list[str]:
    return [
        f"{index}. `{sample['sample_type']}` **{md(sample['company'])} - {md(sample['title'])}**",
        f"   - Skills: {md(sample['final_skills'])}",
        f"   - Excerpt: {md(sample['excerpt'])}",
        f"   - Boundary review: {md(sample['diagnostic_note'])}",
        f"   - URL: {md(sample['job_url'])}",
        "",
    ]


def unique_samples(
    rows: list[dict],
    count: int,
    sample_group: str,
    sample_type: str,
) -> list[dict]:
    selected = []
    seen_ids: set[str] = set()
    for row in rows:
        posting_id = source_id(row)
        if posting_id in seen_ids:
            continue
        selected.append(sample_record(row, sample_group, sample_type))
        seen_ids.add(posting_id)
        if len(selected) >= count:
            break
    return selected


def sample_record(row: dict, sample_group: str, sample_type: str) -> dict:
    boundary_text = (
        f"strongest competing signal: {row['_boundary_role']} "
        f"({', '.join(row['_boundary_hits']) or 'none'}); "
        f"AI service signals: {', '.join(row['_ai_hits']) or 'none'}; "
        f"ML model signals: {', '.join(row['_ml_hits']) or 'none'}"
    )
    return {
        "sample_group": sample_group,
        "sample_type": sample_type,
        "job_role_category": value(row, "job_role_category"),
        "source_posting_id": source_id(row),
        "company": value(row, "company"),
        "title": value(row, "title"),
        "final_skills": value(row, "final_skills"),
        "excerpt": row["_excerpt"],
        "job_url": value(row, "job_url"),
        "ai_backend_signals": "; ".join(row["_ai_hits"]),
        "ml_model_signals": "; ".join(row["_ml_hits"]),
        "boundary_role": row["_boundary_role"],
        "diagnostic_note": boundary_text,
    }


def boundary_priority(role: str, row: dict) -> int:
    score = len(row["_boundary_hits"]) * 10
    if row["_boundary_role"] and row["_boundary_role"] != role:
        score += 20
    if role == "AI Backend Developer" and row["_ml_only"]:
        score += 100
    return score


def strongest_boundary(row: dict[str, str], text: str) -> tuple[str, list[str]]:
    assigned_role = value(row, "job_role_category")
    candidates = []
    for role, signals in BOUNDARY_SIGNALS.items():
        if role == assigned_role:
            continue
        hits = match_signals(text, signals)
        candidates.append((role, hits))
    role, hits = max(candidates, key=lambda item: (len(item[1]), item[0]))
    return (role, hits) if hits else ("none", [])


def boundary_risk_summary(
    first: str,
    second: str,
    shared_skills: list[str],
    shared_title_terms: list[str],
) -> str:
    signals = ", ".join(shared_title_terms[:5]) or "no distinctive shared title term"
    skills = ", ".join(shared_skills[:5]) or "no shared TOP20 skill"
    return (
        f"Shared top-skill evidence includes {skills}; shared title terms include {signals}. "
        f"Documents between {first} and {second} require review when these signals appear "
        "without role-specific context."
    )


def title_token_counts(rows: list[dict]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        tokens = {
            token
            for token in re.findall(r"[a-z][a-z+#.-]{1,}", value(row, "title").lower())
            if token not in TITLE_STOPWORDS
        }
        counts.update(tokens)
    return counts


def match_signals(text: str, signals: dict[str, str]) -> list[str]:
    return [
        name for name, pattern in signals.items() if re.search(pattern, text, flags=re.IGNORECASE)
    ]


def diagnostic_text(row: dict[str, str]) -> str:
    return " ".join(
        value(row, column)
        for column in [
            "title",
            "department",
            "final_skills",
            "responsibilities",
            "requirements",
            "preferred_qualifications",
        ]
    )


def excerpt(row: dict[str, str]) -> str:
    raw_text = (
        value(row, "responsibilities")
        or value(row, "requirements")
        or value(row, "preferred_qualifications")
        or "No description provided."
    )
    text = " ".join(raw_text.split())
    return f"{text[:300].rstrip()}..." if len(text) > 300 else text


def parse_skills(text: str) -> list[str]:
    return [skill.strip() for skill in text.split(";") if skill.strip()]


def source_id(row: dict[str, str]) -> str:
    return value(row, "id") or f"{value(row, 'company')}|{value(row, 'title')}|{value(row, 'job_url')}"


def percentage(count: int, total: int) -> float:
    return count / total * 100 if total else 0.0


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def md(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
