from __future__ import annotations


SKILL_READY_TARGETS = {
    "AI Backend Developer": 100,
    "Backend Developer": 100,
    "Builder": 80,
    "Data Analyst": 80,
    "Data Engineer": 80,
    "Data Scientist": 109,
    "Frontend Developer": 80,
}


ROLE_COLLECTION_RULES = [
    {
        "role": "Builder",
        "priority": 10,
        "include_phrases": [
            "AI Product Engineer",
            "Product Engineer AI",
            "Founding Engineer AI",
            "Full Stack AI Engineer",
            "Applied AI Product Engineer",
            "Prototype Engineer",
            "Automation Engineer",
            "Product Engineer",
        ],
        "exclude_phrases": [
            "Solutions Engineer",
            "Sales Engineer",
            "Pre-Sales",
            "Professional Services",
            "Account Executive",
        ],
    },
    {
        "role": "AI Backend Developer",
        "priority": 20,
        "include_phrases": [
            "AI Backend Engineer",
            "LLM Application Engineer",
            "Generative AI Engineer",
            "Applied AI Engineer",
            "RAG Engineer",
            "AI Platform Engineer",
            "Inference Engineer",
            "Software Engineer AI Platform",
            "LLM Platform Engineer",
        ],
        "exclude_phrases": [
            "Fraud Prediction",
            "Personalization Model",
            "Research Scientist",
            "Recommendation Model",
        ],
    },
    {
        "role": "Frontend Developer",
        "priority": 30,
        "include_phrases": [
            "Frontend Engineer",
            "Front-End Engineer",
            "Frontend Software Engineer",
            "React Engineer",
            "UI Engineer",
            "Web Frontend Engineer",
            "Design Systems Engineer",
            "Frontend Platform Engineer",
        ],
        "exclude_phrases": [],
    },
    {
        "role": "Data Analyst",
        "priority": 40,
        "include_phrases": [
            "Data Analyst",
            "Product Analyst",
            "BI Analyst",
            "Business Intelligence Analyst",
            "Analytics Analyst",
            "Product Analytics Analyst",
            "Growth Analyst",
            "Marketing Analyst",
            "Operations Analyst",
        ],
        "exclude_phrases": [],
    },
    {
        "role": "Data Engineer",
        "priority": 50,
        "include_phrases": [
            "Data Engineer",
            "Analytics Engineer",
            "Data Platform Engineer",
            "ETL Engineer",
            "Data Pipeline Engineer",
        ],
        "exclude_phrases": [],
    },
    {
        "role": "Backend Developer",
        "priority": 60,
        "include_phrases": [
            "Backend Engineer",
            "Back-End Engineer",
            "Backend Developer",
            "API Engineer",
            "Server Engineer",
            "Platform Backend Engineer",
        ],
        "exclude_phrases": [
            "Datacenter",
            "Audiovisual",
            "Hardware Infrastructure",
        ],
    },
]


def active_collection_roles() -> list[str]:
    return [rule["role"] for rule in sorted(ROLE_COLLECTION_RULES, key=lambda item: item["priority"])]
