import pandas as pd


RAW_FILE = "data/raw/cloudcost_billing_50000.csv"


def run_quality_check():

    df = pd.read_csv(RAW_FILE)

    print("\n========== CLOUDPULSE DATA QUALITY REPORT ==========")

    print(f"Rows              : {len(df):,}")
    print(f"Columns           : {len(df.columns)}")

    print("\n--- Missing Values ---")
    missing = df.isnull().sum()
    print(missing[missing > 0] if missing.sum() > 0 else "No missing values")

    print("\n--- Duplicate Rows ---")
    print(f"Duplicates        : {df.duplicated().sum():,}")

    print("\n--- Timestamp Check ---")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    print(f"Invalid timestamps: {df['timestamp'].isna().sum():,}")
    print(f"Start             : {df['timestamp'].min()}")
    print(f"End               : {df['timestamp'].max()}")

    print("\n--- Cost Check ---")
    print(f"Negative costs    : {(df['cost'] < 0).sum():,}")
    print(f"Total cost        : ${df['cost'].sum():,.2f}")
    print(f"Average cost      : ${df['cost'].mean():,.2f}")
    print(f"Median cost       : ${df['cost'].median():,.2f}")

    print("\n--- Dimension Counts ---")
    print(f"Cloud providers   : {df['cloud_provider'].nunique()}")
    print(f"Projects          : {df['project'].nunique()}")
    print(f"Services          : {df['service'].nunique()}")
    print(f"Resources         : {df['resource_id'].nunique()}")
    print(f"Departments       : {df['department'].nunique()}")

    print("\n--- Percentage Validation ---")

    percentage_columns = [
        "cpu_utilization_pct",
        "memory_utilization_pct",
        "storage_utilization_pct",
        "utilization_efficiency_pct",
    ]

    for column in percentage_columns:
        invalid = ((df[column] < 0) | (df[column] > 100)).sum()
        print(f"{column:<32}: {invalid:,} invalid")

    print("\n--- Budget Utilization ---")
    print(
        "Budget over 100% :",
        (df["budget_utilization_pct"] > 100).sum()
    )

    print("\n====================================================")


if __name__ == "__main__":
    run_quality_check()
