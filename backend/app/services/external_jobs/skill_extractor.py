import re


TECH_KEYWORDS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "React",
    "Node.js",
    "FastAPI",
    "Django",
    "Spring",
    "Go",
    "Rust",
    "C++",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "AWS",
    "GCP",
    "Azure",
    "Docker",
    "Kubernetes",
    "Airflow",
    "MLflow",
    "Spark",
    "Kafka",
    "LLM",
    "RAG",
    "LangChain",
    "Vector DB",
    "Embedding",
    "Machine Learning",
    "Deep Learning",
    "TensorFlow",
    "PyTorch",
]


def extract_skills(text: str) -> list[str]:
    if not text:
        return []

    found = []
    for keyword in TECH_KEYWORDS:
        if _matches_keyword(keyword, text):
            found.append(keyword)
    return found


def _matches_keyword(keyword: str, text: str) -> bool:
    if keyword == "Go":
        return re.search(r"(?<![A-Za-z0-9])go(?![A-Za-z0-9-])", text, flags=re.IGNORECASE) is not None

    escaped = re.escape(keyword)
    pattern = rf"(?<![A-Za-z0-9+#.]){escaped}(?![A-Za-z0-9+#.-])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None
