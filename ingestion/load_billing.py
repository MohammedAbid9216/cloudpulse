import csv
import psycopg2
from pathlib import Path


CSV_FILE = Path("data/raw/cloudcost_billing_50000.csv")

DB_CONFIG = {
    "dbname": "cloudpulse",
    "user": "mohdabid",
    "host": "localhost",
    "port": 5432,
}


def load_data():

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"CSV file not found: {CSV_FILE}"
        )

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TEMP TABLE staging_billing
                AS SELECT * FROM raw.cloudcost_billing
                WITH NO DATA;
            """)

            with open(CSV_FILE, "r", encoding="utf-8") as file:
                cur.copy_expert(
                    """
                    COPY staging_billing
                    FROM STDIN
                    WITH (FORMAT CSV, HEADER TRUE)
                    """,
                    file,
                )

            cur.execute("""
                INSERT INTO raw.cloudcost_billing
                SELECT *
                FROM staging_billing
                ON CONFLICT (usage_id) DO NOTHING;
            """)

            inserted = cur.rowcount

            cur.execute("""
                SELECT COUNT(*)
                FROM staging_billing;
            """)

            source_rows = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM raw.cloudcost_billing;
            """)

            total_rows = cur.fetchone()[0]

        conn.commit()

        print("✅ Data ingestion completed")
        print(f"Source rows      : {source_rows:,}")
        print(f"New rows inserted: {inserted:,}")
        print(f"Total DB rows    : {total_rows:,}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    load_data()