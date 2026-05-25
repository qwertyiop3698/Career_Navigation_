import argparse
from datetime import datetime
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.db import Base, SessionLocal, engine
from app.models import JobRoleMarketHistory
from app.services.market_history import collect_adzuna_salary_history


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Adzuna role-level monthly market history.")
    parser.add_argument("--country", default="us")
    parser.add_argument("--start-month", default="2021-02")
    args = parser.parse_args()

    start_month = datetime.strptime(args.start_month, "%Y-%m").date().replace(day=1)
    Base.metadata.create_all(bind=engine, tables=[JobRoleMarketHistory.__table__])

    db = SessionLocal()
    try:
        result = collect_adzuna_salary_history(
            db=db,
            country=args.country,
            start_month=start_month,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(result)


if __name__ == "__main__":
    main()
