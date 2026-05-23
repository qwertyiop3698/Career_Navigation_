import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.external_jobs.ats_collectors import collect_all_external_jobs


def main():
    result = collect_all_external_jobs()

    print("Company results:")
    for company_result in result["company_results"]:
        print(
            f"- {company_result['company']} "
            f"({company_result['source']}): "
            f"{company_result['status']}, fetched={company_result['fetched']}"
        )
        if company_result.get("reason"):
            print(f"  reason={company_result['reason']}")

    print(f"\nTotal fetched: {result['total_fetched']}")
    print("\nSample jobs:")
    for job in result["jobs"][:5]:
        print(
            f"- [{job['source']}] {job['company']} | "
            f"{job['title']} | {job.get('location') or '-'}"
        )
        print(f"  {job.get('job_url') or '-'}")


if __name__ == "__main__":
    main()
