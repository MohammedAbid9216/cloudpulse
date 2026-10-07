import pandas as pd


RAW_FILE = "data/raw/cloudcost_billing_50000.csv"


def main():

    df = pd.read_csv(RAW_FILE)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)

    print("\n========== CLOUDPULSE EDA ==========")

    # -------------------------------------------------
    # 1. OVERALL KPIs
    # -------------------------------------------------

    print("\n========== OVERALL KPIs ==========")

    print(f"Total Cost       : ${df['cost'].sum():,.2f}")
    print(f"Average Cost     : ${df['cost'].mean():,.2f}")
    print(f"Median Cost      : ${df['cost'].median():,.2f}")
    print(f"Resources        : {df['resource_id'].nunique():,}")
    print(f"Projects         : {df['project'].nunique():,}")
    print(f"Cloud Providers  : {df['cloud_provider'].nunique():,}")

    # -------------------------------------------------
    # 2. COST BY CLOUD PROVIDER
    # -------------------------------------------------

    print("\n========== COST BY CLOUD PROVIDER ==========")

    provider = (
        df.groupby("cloud_provider")
        .agg(
            total_cost=("cost", "sum"),
            avg_cost=("cost", "mean"),
            records=("usage_id", "count"),
            resources=("resource_id", "nunique"),
        )
        .sort_values("total_cost", ascending=False)
    )

    print(provider.to_string())

    # -------------------------------------------------
    # 3. COST BY PROJECT
    # -------------------------------------------------

    print("\n========== COST BY PROJECT ==========")

    project = (
        df.groupby("project")
        .agg(
            total_cost=("cost", "sum"),
            avg_cost=("cost", "mean"),
            resources=("resource_id", "nunique"),
            budget_utilization=("budget_utilization_pct", "mean"),
        )
        .sort_values("total_cost", ascending=False)
    )

    print(project.to_string())

    # -------------------------------------------------
    # 4. COST BY SERVICE
    # -------------------------------------------------

    print("\n========== COST BY SERVICE ==========")

    service = (
        df.groupby("service")
        .agg(
            total_cost=("cost", "sum"),
            avg_cost=("cost", "mean"),
            records=("usage_id", "count"),
        )
        .sort_values("total_cost", ascending=False)
    )

    print(service.to_string())

    # -------------------------------------------------
    # 5. COST BY DEPARTMENT
    # -------------------------------------------------

    print("\n========== COST BY DEPARTMENT ==========")

    department = (
        df.groupby("department")
        .agg(
            total_cost=("cost", "sum"),
            avg_cost=("cost", "mean"),
            resources=("resource_id", "nunique"),
        )
        .sort_values("total_cost", ascending=False)
    )

    print(department.to_string())

    # -------------------------------------------------
    # 6. MONTHLY COST TREND
    # -------------------------------------------------

    print("\n========== MONTHLY COST TREND ==========")

    monthly = (
        df.groupby("month")
        .agg(
            total_cost=("cost", "sum"),
            avg_cost=("cost", "mean"),
            records=("usage_id", "count"),
        )
        .sort_index()
    )

    print(monthly.to_string())

    # -------------------------------------------------
    # 7. BUDGET OVERRUN
    # -------------------------------------------------

    print("\n========== BUDGET OVERRUN ==========")

    over_budget = df[df["budget_utilization_pct"] > 100]

    print(f"Records over budget : {len(over_budget):,}")
    print(f"Cost of over-budget records : ${over_budget['cost'].sum():,.2f}")

    project_budget = (
        df.groupby("project")
        .agg(
            avg_budget_utilization=("budget_utilization_pct", "mean"),
            max_budget_utilization=("budget_utilization_pct", "max"),
            total_cost=("cost", "sum"),
        )
        .sort_values("avg_budget_utilization", ascending=False)
    )

    print(project_budget.to_string())

    # -------------------------------------------------
    # 8. LOW UTILIZATION + HIGH COST
    # -------------------------------------------------

    print("\n========== LOW UTILIZATION + HIGH COST ==========")

    high_cost_threshold = df["cost"].quantile(0.90)

    inefficient = df[
        (df["cost"] >= high_cost_threshold)
        & (df["utilization_efficiency_pct"] < 30)
    ]

    print(f"High-cost inefficient records : {len(inefficient):,}")

    print(
        inefficient[
            [
                "resource_id",
                "project",
                "service",
                "cost",
                "cpu_utilization_pct",
                "memory_utilization_pct",
                "utilization_efficiency_pct",
            ]
        ]
        .sort_values("cost", ascending=False)
        .head(20)
        .to_string(index=False)
    )

    # -------------------------------------------------
    # 9. HIGH COST GROWTH
    # -------------------------------------------------

    print("\n========== HIGH COST GROWTH ==========")

    high_growth = (
        df.sort_values("cost_growth_pct", ascending=False)
        [
            [
                "timestamp",
                "project",
                "resource_id",
                "cost",
                "previous_period_cost",
                "cost_growth_pct",
            ]
        ]
        .head(20)
    )

    print(high_growth.to_string(index=False))

    # -------------------------------------------------
    # 10. RESOURCE STATUS
    # -------------------------------------------------

    print("\n========== RESOURCE STATUS ==========")

    status = (
        df.groupby("resource_status")
        .agg(
            total_cost=("cost", "sum"),
            records=("usage_id", "count"),
            resources=("resource_id", "nunique"),
        )
        .sort_values("total_cost", ascending=False)
    )

    print(status.to_string())

    print("\n====================================")
    print("EDA COMPLETE")
    print("====================================")


if __name__ == "__main__":
    main()
