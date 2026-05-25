import argparse
import csv
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer


INPUT_FIELDS = [
    "title",
    "job_role_category",
    "department",
    "responsibilities",
    "requirements",
    "preferred_qualifications",
]

OUTPUT_EXTRA_FIELDS = [
    "predicted_skills",
    "predicted_skill_scores",
    "final_skills",
    "skills_method",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict missing skills with TF-IDF + Logistic Regression.")
    parser.add_argument(
        "--input",
        default="backend/data/exports/external_job_postings_role_analysis.csv",
    )
    parser.add_argument(
        "--output",
        default="backend/data/exports/external_job_postings_role_analysis_ml_skills.csv",
    )
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--max-predictions", type=int, default=5)
    parser.add_argument("--min-label-count", type=int, default=8)
    args = parser.parse_args()

    rows = read_csv(Path(args.input))
    labeled_rows = [row for row in rows if parse_skills(row.get("skills"))]
    missing_rows = [row for row in rows if not parse_skills(row.get("skills"))]

    label_counts = count_labels(labeled_rows)
    allowed_labels = {
        label
        for label, count in label_counts.items()
        if count >= args.min_label_count
    }
    train_rows = [
        row
        for row in labeled_rows
        if [skill for skill in parse_skills(row.get("skills")) if skill in allowed_labels]
    ]

    texts = [build_text(row) for row in train_rows]
    labels = [
        [skill for skill in parse_skills(row.get("skills")) if skill in allowed_labels]
        for row in train_rows
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9,
        max_features=30000,
        stop_words="english",
    )
    mlb = MultiLabelBinarizer(classes=sorted(allowed_labels))
    x = vectorizer.fit_transform(texts)
    y = mlb.fit_transform(labels)

    classifier = OneVsRestClassifier(
        LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            solver="liblinear",
        )
    )

    metrics = {}
    if len(train_rows) >= 50 and y.shape[1] > 1:
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.2,
            random_state=42,
        )
        classifier.fit(x_train, y_train)
        y_pred = classifier.predict(x_test)
        metrics = {
            "micro_f1": round(f1_score(y_test, y_pred, average="micro", zero_division=0), 4),
            "macro_f1": round(f1_score(y_test, y_pred, average="macro", zero_division=0), 4),
        }

    classifier.fit(x, y)

    filled_count = 0
    for row in rows:
        existing_skills = parse_skills(row.get("skills"))
        if existing_skills:
            row["predicted_skills"] = ""
            row["predicted_skill_scores"] = ""
            row["final_skills"] = format_skills(existing_skills)
            row["skills_method"] = "keyword"
            continue

        predicted = predict_skills(
            classifier=classifier,
            vectorizer=vectorizer,
            classes=list(mlb.classes_),
            text=build_text(row),
            threshold=args.threshold,
            max_predictions=args.max_predictions,
        )
        row["predicted_skills"] = format_skills([skill for skill, _ in predicted])
        row["predicted_skill_scores"] = "; ".join(
            f"{skill}:{score:.3f}" for skill, score in predicted
        )
        row["final_skills"] = row["predicted_skills"]
        row["skills_method"] = "model" if predicted else "missing"
        if predicted:
            filled_count += 1

    write_csv(Path(args.output), rows)
    print(
        {
            "input_rows": len(rows),
            "labeled_rows": len(labeled_rows),
            "missing_rows": len(missing_rows),
            "train_rows": len(train_rows),
            "labels": len(allowed_labels),
            "threshold": args.threshold,
            "filled_missing_rows": filled_count,
            "still_missing_rows": len(missing_rows) - filled_count,
            **metrics,
            "output": args.output,
        }
    )


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    for field in OUTPUT_EXTRA_FIELDS:
        if field not in fields:
            fields.append(field)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_skills(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def format_skills(skills: list[str]) -> str:
    seen = set()
    output = []
    for skill in skills:
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(skill)
    return "; ".join(output)


def build_text(row: dict) -> str:
    return " ".join(str(row.get(field) or "") for field in INPUT_FIELDS)


def count_labels(rows: list[dict]) -> dict[str, int]:
    counts = {}
    for row in rows:
        for skill in parse_skills(row.get("skills")):
            counts[skill] = counts.get(skill, 0) + 1
    return counts


def predict_skills(
    classifier,
    vectorizer,
    classes: list[str],
    text: str,
    threshold: float,
    max_predictions: int,
) -> list[tuple[str, float]]:
    x = vectorizer.transform([text])
    probabilities = classifier.predict_proba(x)[0]
    ranked = sorted(
        zip(classes, probabilities),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        (skill, float(score))
        for skill, score in ranked
        if score >= threshold
    ][:max_predictions]


if __name__ == "__main__":
    main()
