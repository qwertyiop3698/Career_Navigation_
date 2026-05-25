from __future__ import annotations

import re


TARGET_ROLES = [
    "AI Backend Developer",
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Frontend Developer",
    "Backend Developer",
    "Builder",
]

HARD_EXCLUDE_PATTERNS = [
    r"\b(account|sales|marketing|finance|payroll|legal|compliance)\b",
    r"\b(recruiter|recruiting|people|human resources|customer success)\b",
    r"\b(operations|partnerships?|business development|support)\b",
    r"\b(product|program|project|engineering|design)\s+manager\b",
    r"\b(manager|director|head|vice president|vp|chief)\b",
    r"\b(designer|counsel|attorney|paralegal)\b",
    r"\bcommunity\b",
    r"\b(android|ios|mobile|security|site reliability|sre|devops|qa|test)\b",
]

ROLE_TITLE_RULES = [
    (
        "AI Backend Developer",
        [
            r"\b(ai|ml|machine learning|llm|agent(ic)?|inference|generative ai)\b.*\b(engineer|developer)\b",
            r"\b(engineer|developer)\b.*\b(ai|ml|machine learning|llm|agent(ic)?|inference|generative ai)\b",
        ],
    ),
    (
        "Data Scientist",
        [
            r"\b(data|applied|research|machine learning)\s+scientist\b",
            r"\bscientist\b.*\b(data|machine learning|ml|ai)\b",
        ],
    ),
    (
        "Data Engineer",
        [
            r"\b(data|analytics|etl|database)\s+engineer\b",
            r"\bdata\s+platform\s+engineer\b",
            r"\bengineer\b.*\b(data platform|data pipeline|etl|analytics engineering)\b",
        ],
    ),
    (
        "Data Analyst",
        [
            r"\b(data|analytics|business intelligence|bi|product analytics)\s+analyst\b",
            r"\banalyst\b.*\b(data|analytics|business intelligence|bi)\b",
        ],
    ),
    (
        "Frontend Developer",
        [
            r"\b(front[- ]?end|frontend|ui|web)\s+(engineer|developer)\b",
            r"\b(front[- ]?end|frontend)\b.*\b(engineer|developer)\b",
            r"\b(engineer|developer)\b.*\b(front[- ]?end|frontend)\b",
        ],
    ),
    (
        "Backend Developer",
        [
            r"\b(back[- ]?end|backend|api|server)\s*(/|\s|-)*(engineer|developer)\b",
            r"\b(engineer|developer)\b.*\b(back[- ]?end|backend|api|server)\b",
            r"\b(platform|infrastructure|distributed systems)\s+engineer\b",
        ],
    ),
    (
        "Builder",
        [
            r"\b(full[- ]?stack|fullstack|founding|product)\s+(engineer|developer)\b",
            r"\b(forward deployed|solutions?|implementation)\s+(engineer|developer)\b",
            r"\bdeveloper advocate\b",
            r"\btechnical founder\b",
        ],
    ),
]


def classify_role(title: str) -> str:
    normalized = " ".join(title.lower().split())
    if _matches_any(normalized, HARD_EXCLUDE_PATTERNS):
        return "Other"
    for role, patterns in ROLE_TITLE_RULES:
        if _matches_any(normalized, patterns):
            return role
    return "Other"


def _matches_any(value: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)
