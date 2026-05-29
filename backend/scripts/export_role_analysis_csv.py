import argparse
import csv
import html
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]
import sys

sys.path.append(str(ROOT_DIR))

from app.db import SessionLocal
from app.models import ExternalJobPosting
from app.services.external_jobs.skill_extractor import extract_skills


OUTPUT_FIELDS = [
    "id",
    "company",
    "title",
    "job_role_category",
    "location",
    "department",
    "skills",
    "responsibilities",
    "requirements",
    "preferred_qualifications",
    "job_url",
    "source",
    "collected_at",
]

ROLE_RULES = [
    (
        "AI Backend Developer",
        [
            r"\bai engineer\b",
            r"\bllm\b",
            r"\brag\b",
            r"\bagent(ic)?\b",
            r"\bprompt engineer",
            r"\bmodel serving\b",
            r"\binference\b",
            r"\bvector (database|db|search)\b",
            r"\bembedding(s)?\b",
            r"\blangchain\b",
            r"\bllamaindex\b",
            r"\bml platform\b",
        ],
    ),
    (
        "Data Scientist",
        [
            r"\bdata scientist\b",
            r"\bmachine learning scientist\b",
            r"\bresearch scientist\b",
            r"\bapplied scientist\b",
            r"\bcausal inference\b",
            r"\bstatistical model",
            r"\bpredictive model",
            r"\bexperiment(s|ation)?\b",
            r"\bforecasting\b",
        ],
    ),
    (
        "Data Engineer",
        [
            r"\bdata engineer\b",
            r"\bdata platform\b",
            r"\bdata pipeline",
            r"\betl\b",
            r"\belt\b",
            r"\bwarehouse\b",
            r"\bspark\b",
            r"\bairflow\b",
            r"\bdbt\b",
            r"\bsnowflake\b",
            r"\bbigquery\b",
            r"\bdatabricks\b",
            r"\bkafka\b",
            r"\blakehouse\b",
        ],
    ),
    (
        "Data Analyst",
        [
            r"\bdata analyst\b",
            r"\banalytics\b",
            r"\bbusiness intelligence\b",
            r"\bbi analyst\b",
            r"\bdashboard",
            r"\breporting\b",
            r"\btableau\b",
            r"\bpower bi\b",
            r"\blooker\b",
            r"\bproduct analyst\b",
            r"\bgrowth analyst\b",
        ],
    ),
    (
        "Frontend Developer",
        [
            r"\bfront[- ]?end\b",
            r"\bfrontend\b",
            r"\bweb engineer\b",
            r"\bui engineer\b",
            r"\breact\b",
            r"\btypescript\b",
            r"\bjavascript\b",
            r"\bnext\.?js\b",
            r"\bvue\b",
            r"\bangular\b",
            r"\bdesign system\b",
        ],
    ),
    (
        "Backend Developer",
        [
            r"\bback[- ]?end\b",
            r"\bbackend\b",
            r"\bserver\b",
            r"\bapi engineer\b",
            r"\bplatform engineer\b",
            r"\binfrastructure engineer\b",
            r"\bdistributed systems\b",
            r"\bmicroservice",
            r"\bdatabase\b",
        ],
    ),
    (
        "Builder",
        [
            r"\bfounding engineer\b",
            r"\bfounder\b",
            r"\bbuilder\b",
            r"\bproduct engineer\b",
            r"\bfull[- ]?stack\b",
            r"\bsolutions engineer\b",
            r"\bforward deployed\b",
            r"\bimplementation engineer\b",
            r"\bdeveloper advocate\b",
            r"\btechnical founder\b",
        ],
    ),
]

EXCLUDE_TITLE_PATTERNS = [
    r"\baccount(s|ing)?\b",
    r"\breceivable\b",
    r"\badministrative\b",
    r"\bcoordinator\b",
    r"\baccount executive\b",
    r"\bsales\b",
    r"\bcustomer success\b",
    r"\bmarketing\b",
    r"\brecruiter\b",
    r"\bpeople\b",
    r"\bhr\b",
    r"\blegal\b",
    r"\bfinance\b",
    r"\bpayroll\b",
    r"\boperations\b",
    r"\bbusiness development\b",
    r"\bpartnership",
    r"\bprogram manager\b",
    r"\bproduct manager\b",
    r"\bdesigner\b",
    r"\bsupport\b",
]

TECH_TITLE_HINT_PATTERNS = [
    r"\bengineer",
    r"\bdeveloper\b",
    r"\barchitect\b",
    r"\bscientist\b",
    r"\bdata\b",
    r"\banalytics\b",
    r"\bmachine learning\b",
    r"\bml\b",
    r"\bai\b",
    r"\bbackend\b",
    r"\bfrontend\b",
    r"\bplatform\b",
    r"\binfrastructure\b",
    r"\bfull[- ]?stack\b",
    r"\btechnical\b",
]

BOILERPLATE_SECTION_PATTERNS = [
    r"\bbenefits?\b",
    r"\bcompensation\b",
    r"\bpay transparency\b",
    r"\bequal opportunity\b",
    r"\beeoc?\b",
    r"\bprivacy\b",
    r"\baccommodation",
    r"\babout us\b",
    r"\babout the company\b",
    r"\bperks\b",
]

RESPONSIBILITY_PATTERNS = [
    r"about the role",
    r"about this role",
    r"responsibilities",
    r"your responsibilities",
    r"what you.?ll do",
    r"what you.?ll be doing",
    r"what you will do",
    r"the impact you.?ll have",
    r"key responsibilities",
]

REQUIREMENT_PATTERNS = [
    r"requirements",
    r"qualifications",
    r"minimum qualifications",
    r"what we look for",
    r"what we.?re looking for",
    r"what we are looking for",
    r"who you are",
    r"you have",
    r"you might thrive in this role if",
]

PREFERRED_PATTERNS = [
    r"preferred qualifications",
    r"nice to have",
    r"bonus",
    r"preferred",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export role-focused analysis CSV.")
    parser.add_argument(
        "--output",
        default="data/exports/external_job_postings_role_analysis.csv",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        postings = db.query(ExternalJobPosting).order_by(ExternalJobPosting.id.asc()).all()
        rows = []
        skipped = 0
        for posting in postings:
            role = classify_role(posting)
            if role == "Other":
                skipped += 1
                continue

            clean_text = clean_description(posting.description or "")
            sections = extract_sections(clean_text)
            skills = extract_skills(
                " ".join(
                    [
                        posting.title or "",
                        posting.department or "",
                        clean_text,
                    ]
                )
            )

            rows.append(
                {
                    "id": posting.id,
                    "company": posting.company,
                    "title": posting.title,
                    "job_role_category": role,
                    "location": posting.location,
                    "department": posting.department,
                    "skills": "; ".join(skills),
                    "responsibilities": sections["responsibilities"],
                    "requirements": sections["requirements"],
                    "preferred_qualifications": sections["preferred_qualifications"],
                    "job_url": posting.job_url,
                    "source": posting.source,
                    "collected_at": posting.collected_at,
                }
            )

        output_path = ROOT_DIR / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        print(
            {
                "output": str(output_path),
                "exported": len(rows),
                "skipped_other": skipped,
                "total": len(postings),
            }
        )
    finally:
        db.close()


def classify_role(posting: ExternalJobPosting) -> str:
    title = posting.title or ""
    title_department = " ".join([posting.title or "", posting.department or ""]).lower()
    haystack = " ".join(
        [
            posting.title or "",
            posting.department or "",
            posting.description or "",
            " ".join(posting.skills or []),
        ]
    ).lower()

    if _matches_any(title.lower(), EXCLUDE_TITLE_PATTERNS):
        return "Other"

    for role, patterns in ROLE_RULES:
        if _matches_any(title_department, patterns):
            return role

    if not _matches_any(title_department, TECH_TITLE_HINT_PATTERNS):
        return "Other"

    for role, patterns in ROLE_RULES:
        if _matches_any(haystack, patterns):
            return role
    return "Other"


def clean_description(description: str) -> str:
    text = normalize_description_text(description or "")
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()).strip()
        if not line:
            continue
        if _matches_any(line.lower(), BOILERPLATE_SECTION_PATTERNS):
            break
        lines.append(line)
    return _truncate("\n".join(lines), 8000)


def normalize_description_text(description: str) -> str:
    text = html.unescape(description or "")
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "\n- ",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"<\s*(br|/p|/li|/h[1-6]|/div)\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<\s*(p|li|h[1-6]|div|ul|ol)\b[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_sections(text: str) -> dict[str, str]:
    normalized = normalize_description_text(text)
    structured = extract_sections_by_heading(normalized)
    if structured:
        return structured

    sentences = split_sentences(normalized)
    responsibilities = []
    requirements = []
    preferred = []

    for sentence in sentences:
        lowered = sentence.lower()
        if _matches_any(lowered, PREFERRED_PATTERNS):
            preferred.append(sentence)
        elif _matches_any(lowered, REQUIREMENT_PATTERNS):
            requirements.append(sentence)
        elif _matches_any(lowered, RESPONSIBILITY_PATTERNS):
            responsibilities.append(sentence)

    if not responsibilities:
        responsibilities = sentences[:4]
    if not requirements:
        requirements = [
            sentence
            for sentence in sentences
            if re.search(r"\b(experience|proficient|knowledge|ability|skills?|build|develop)\b", sentence, re.I)
        ][:5]

    return {
        "responsibilities": _truncate(" ".join(responsibilities), 1200),
        "requirements": _truncate(" ".join(requirements), 1200),
        "preferred_qualifications": _truncate(" ".join(preferred), 800),
    }


def split_sentences(text: str) -> list[str]:
    marked = mark_inline_headings(text)
    parts = re.split(r"(?<=[.!?])\s+|\n+|(?=\s[-*]\s)", marked)
    return [part.strip(" -*\t") for part in parts if len(part.strip(" -*\t")) > 30]


HEADING_GROUPS = [
    (
        "responsibilities",
        [
            r"about the role",
            r"about this role",
            r"what you'?ll do",
            r"what you'll be doing",
            r"what you will do",
            r"responsibilities",
            r"your responsibilities",
            r"key responsibilities",
            r"the impact you'?ll have",
        ],
    ),
    (
        "requirements",
        [
            r"requirements",
            r"qualifications",
            r"minimum qualifications",
            r"what we look for",
            r"what we're looking for",
            r"what we are looking for",
            r"who you are",
            r"you have",
            r"you might thrive in this role if",
        ],
    ),
    (
        "preferred_qualifications",
        [
            r"preferred qualifications",
            r"nice to have",
            r"bonus",
            r"preferred",
        ],
    ),
]


def extract_sections_by_heading(text: str) -> dict[str, str] | None:
    marked = mark_inline_headings(text)
    chunks = split_marked_sections(marked)
    if not chunks:
        return None
    grouped = {"responsibilities": [], "requirements": [], "preferred_qualifications": []}
    current = ""
    for chunk in chunks:
        heading = classify_heading(chunk)
        if heading:
            current = heading
            content = remove_heading(chunk)
        else:
            content = chunk
        if current and content:
            grouped[current].append(content)
    if not any(grouped.values()):
        return None
    return {
        "responsibilities": _truncate(" ".join(grouped["responsibilities"]), 1600),
        "requirements": _truncate(" ".join(grouped["requirements"]), 1600),
        "preferred_qualifications": _truncate(" ".join(grouped["preferred_qualifications"]), 1000),
    }


def mark_inline_headings(text: str) -> str:
    marked = text
    all_headings = [pattern for _, patterns in HEADING_GROUPS for pattern in patterns]
    for pattern in sorted(all_headings, key=len, reverse=True):
        marked = re.sub(
            rf"(?<![A-Za-z])({pattern})(\s*:)?",
            lambda match: "\n" + match.group(1) + (match.group(2) or "") + "\n",
            marked,
            flags=re.I,
        )
    return re.sub(r"\n\s*\n+", "\n", marked).strip()


def split_marked_sections(text: str) -> list[str]:
    return [part.strip(" -*\t") for part in re.split(r"\n+", text) if len(part.strip(" -*\t")) > 2]


def classify_heading(text: str) -> str:
    lowered = text.lower().strip(" :")
    for field, patterns in HEADING_GROUPS:
        if any(re.fullmatch(pattern, lowered, flags=re.I) for pattern in patterns):
            return field
    return ""


def remove_heading(text: str) -> str:
    cleaned = text.strip()
    for _, patterns in HEADING_GROUPS:
        for pattern in patterns:
            cleaned = re.sub(rf"^{pattern}\s*:?\s*", "", cleaned, flags=re.I)
    return cleaned.strip(" :-")


def _matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


if __name__ == "__main__":
    main()
