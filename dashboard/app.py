import streamlit as st
from sqlalchemy import create_engine, text, bindparam
import pandas as pd
import plotly.express as px
from datetime import datetime


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="CloudPulse",
    page_icon="☁️",
    layout="wide",
)

# Auto-refresh dashboard every 60 seconds
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60 * 1000, key="cloudpulse_refresh")
except ImportError:
    pass


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

@st.cache_resource
def get_connection():
    return create_engine(
        "postgresql+psycopg2://mohdabid@localhost:5432/cloudpulse",
        pool_pre_ping=True,
    )


def load_filter_options():
    engine = get_connection()

    options = {}

    columns = [
        "cloud_provider",
        "project",
        "department",
        "environment",
        "region",
        "service",
        "owner_team",
    ]

    with engine.connect() as conn:
        for column in columns:
            result = conn.execute(
                text(
                    f"""
                    SELECT DISTINCT {column}
                    FROM raw.cloudcost_billing
                    WHERE {column} IS NOT NULL
                    ORDER BY {column}
                    """
                )
            )
            options[column] = [row[0] for row in result.fetchall()]

    return options


def load_filtered_data(
    start_date,
    end_date,
    cloud_provider,
    project,
    department,
    environment,
    region,
    service,
    owner_team,
):
    engine = get_connection()

    query = """
        SELECT *
        FROM raw.cloudcost_billing
        WHERE timestamp::date BETWEEN :start_date AND :end_date
    """

    params = {
        "start_date": start_date,
        "end_date": end_date,
    }

    expanding_params = []

    filters = {
        "cloud_provider": cloud_provider,
        "project": project,
        "department": department,
        "environment": environment,
        "region": region,
        "service": service,
        "owner_team": owner_team,
    }

    for column, values in filters.items():
        if values:
            query += f" AND {column} IN :{column}"
            params[column] = values
            expanding_params.append(column)

    statement = text(query)

    for parameter in expanding_params:
        statement = statement.bindparams(
            bindparam(parameter, expanding=True)
        )

    with engine.connect() as conn:
        return pd.read_sql_query(
            statement,
            conn,
            params=params,
        )


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("☁️ CloudPulse")
st.caption("Cloud Cost Analytics & Optimization Dashboard")


# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("🔎 Filters")

options = load_filter_options()

start_date = st.sidebar.date_input(
    "Start Date",
    value=datetime(2025, 9, 1).date(),
    min_value=datetime(2025, 9, 1).date(),
    max_value=datetime(2026, 8, 31).date(),
)

end_date = st.sidebar.date_input(
    "End Date",
    value=datetime(2026, 8, 31).date(),
    min_value=datetime(2025, 9, 1).date(),
    max_value=datetime(2026, 8, 31).date(),
)


cloud_provider = st.sidebar.multiselect(
    "Cloud Provider",
    options["cloud_provider"],
)

project = st.sidebar.multiselect(
    "Project",
    options["project"],
)

department = st.sidebar.multiselect(
    "Department",
    options["department"],
)

environment = st.sidebar.multiselect(
    "Environment",
    options["environment"],
)

region = st.sidebar.multiselect(
    "Region",
    options["region"],
)

service = st.sidebar.multiselect(
    "Service",
    options["service"],
)

owner_team = st.sidebar.multiselect(
    "Owner Team",
    options["owner_team"],
)


# --------------------------------------------------
# VALIDATE DATE
# --------------------------------------------------

if start_date > end_date:
    st.error("Start Date cannot be after End Date.")
    st.stop()


# --------------------------------------------------
# REFRESH
# --------------------------------------------------

if st.sidebar.button("🔄 Refresh Data", width="stretch"):
    st.cache_data.clear()
    st.rerun()


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

df = load_filtered_data(
    start_date=start_date,
    end_date=end_date,
    cloud_provider=cloud_provider,
    project=project,
    department=department,
    environment=environment,
    region=region,
    service=service,
    owner_team=owner_team,
)


if df.empty:
    st.warning("No data found for the selected filters.")
    st.stop()


df["timestamp"] = pd.to_datetime(df["timestamp"])


# --------------------------------------------------
# KPI CALCULATIONS
# --------------------------------------------------

total_cost = df["cost"].sum()

average_cost = df["cost"].mean()

active_resources = df.loc[
    df["resource_status"].isin(["Running", "Stopped", "Terminated"]),
    "resource_id",
].nunique()

projects = df["project"].nunique()

cloud_providers = df["cloud_provider"].nunique()

over_budget_records = (
    df["budget_utilization_pct"] > 100
).sum()

over_budget_cost = df.loc[
    df["budget_utilization_pct"] > 100,
    "cost",
].sum()

average_budget_utilization = df[
    "budget_utilization_pct"
].mean()

high_cost_threshold = df["cost"].quantile(0.90)

high_cost_low_efficiency = df[
    (df["cost"] >= high_cost_threshold)
    & (df["utilization_efficiency_pct"] < 30)
]["resource_id"].nunique()


# --------------------------------------------------

# --------------------------------------------------
# DASHBOARD NAVIGATION
# --------------------------------------------------

dashboard_page = st.sidebar.radio(
    "📊 Dashboard Pages",
    [
        "🏠 Executive Overview",
        "💰 Cost Analysis",
        "🎯 Resource Efficiency",
        "🚨 Budget & Anomalies",
        "🤖 ML / Forecast Handoff",
    ],
)

if dashboard_page == "🏠 Executive Overview":

    st.subheader("Executive Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Cloud Cost",
        f"${total_cost:,.2f}",
    )

    col2.metric(
        "Average Cost",
        f"${average_cost:,.2f}",
    )

    col3.metric(
        "Active Resources",
        f"{active_resources:,}",
    )

    col4.metric(
        "Projects",
        f"{projects:,}",
    )

    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "Cloud Providers",
        f"{cloud_providers:,}",
    )

    col6.metric(
        "Over-Budget Records",
        f"{over_budget_records:,}",
    )

    col7.metric(
        "Over-Budget Cost",
        f"${over_budget_cost:,.2f}",
    )

    col8.metric(
        "Low-Efficiency Resources",
        f"{high_cost_low_efficiency:,}",
    )


    # --------------------------------------------------
    # ACTIVE FILTER SUMMARY
    # --------------------------------------------------

    st.info(
        f"Showing {len(df):,} records | "
        f"{df['resource_id'].nunique():,} resources | "
        f"{start_date} → {end_date}"
    )


    # --------------------------------------------------


    # --------------------------------------------------
    # BUSINESS INSIGHTS & ACTIONS
    # --------------------------------------------------

    st.subheader("📌 Business Insights & Actions")

    provider_costs = (
        df.groupby("cloud_provider")["cost"]
        .sum()
        .sort_values(ascending=False)
    )

    project_costs = (
        df.groupby("project")["cost"]
        .sum()
        .sort_values(ascending=False)
    )

    service_costs = (
        df.groupby("service")["cost"]
        .sum()
        .sort_values(ascending=False)
    )

    department_costs = (
        df.groupby("department")["cost"]
        .sum()
        .sort_values(ascending=False)
    )

    monthly_insight = (
        df.assign(month=df["timestamp"].dt.to_period("M"))
        .groupby("month")["cost"]
        .sum()
        .sort_index()
    )

    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:
        if not provider_costs.empty and total_cost > 0:
            provider_name = provider_costs.index[0]
            provider_value = provider_costs.iloc[0]
            provider_share = provider_value / total_cost * 100

            st.info(
                f"☁️ **Provider concentration:** {provider_name} accounts for "
                f"**{provider_share:.1f}%** of filtered cloud spend "
                f"(${provider_value:,.2f})."
            )

        if not project_costs.empty:
            project_name = project_costs.index[0]
            project_value = project_costs.iloc[0]

            st.info(
                f"📊 **Highest-cost project:** {project_name} at "
                f"**${project_value:,.2f}**."
            )

        if not service_costs.empty:
            service_name = service_costs.index[0]
            service_value = service_costs.iloc[0]

            st.info(
                f"⚙️ **Highest-cost service:** {service_name} at "
                f"**${service_value:,.2f}**."
            )

    with insight_col2:
        if not department_costs.empty:
            department_name = department_costs.index[0]
            department_value = department_costs.iloc[0]

            st.info(
                f"🏢 **Highest-cost department:** {department_name} at "
                f"**${department_value:,.2f}**."
            )

        if total_cost > 0:
            budget_exposure = over_budget_cost / total_cost * 100

            st.warning(
                f"💰 **Budget exposure:** ${over_budget_cost:,.2f} is associated "
                f"with over-budget records ({budget_exposure:.1f}% of filtered cost)."
            )

        if len(monthly_insight) >= 2:
            latest_month = monthly_insight.iloc[-1]
            previous_month = monthly_insight.iloc[-2]

            if previous_month > 0:
                monthly_change = (
                    (latest_month - previous_month)
                    / previous_month
                    * 100
                )

                direction = (
                    "increased"
                    if monthly_change >= 0
                    else "decreased"
                )

                st.info(
                    f"📈 **Latest monthly movement:** Cloud cost "
                    f"{direction} by **{abs(monthly_change):.1f}%** "
                    f"versus the previous month."
                )

    st.subheader("🎯 Recommended Management Actions")

    actions = []

    if over_budget_records > 0:
        actions.append(
            f"Review the {over_budget_records:,} over-budget records "
            f"representing ${over_budget_cost:,.2f} of cost exposure."
        )

    if high_cost_low_efficiency > 0:
        actions.append(
            f"Investigate {high_cost_low_efficiency:,} high-cost resources "
            f"with utilization efficiency below 30%."
        )

    if not provider_costs.empty:
        actions.append(
            f"Review {provider_costs.index[0]} spend concentration "
            f"for potential optimization opportunities."
        )

    if not service_costs.empty:
        actions.append(
            f"Prioritize {service_costs.index[0]} because it is the "
            f"highest-cost service in the selected data."
        )

    if not project_costs.empty:
        actions.append(
            f"Investigate {project_costs.index[0]} as the largest "
            f"project-level cost contributor."
        )

    for i, action in enumerate(actions[:5], start=1):
        st.write(f"**{i}.** {action}")


if dashboard_page == "💰 Cost Analysis":

    # COST BY PROVIDER
    # --------------------------------------------------

    st.subheader("☁️ Cost by Cloud Provider")

    provider_df = (
        df.groupby("cloud_provider", as_index=False)
        .agg(
            total_cost=("cost", "sum"),
            records=("usage_id", "count"),
        )
        .sort_values("total_cost", ascending=False)
    )

    fig_provider = px.bar(
        provider_df,
        x="cloud_provider",
        y="total_cost",
        text_auto=".2s",
        title="Total Cost by Cloud Provider",
    )

    fig_provider.update_layout(
        xaxis_title="Cloud Provider",
        yaxis_title="Cost ($)",
    )

    st.plotly_chart(
        fig_provider,
        width="stretch",
    )


    # --------------------------------------------------
    # MONTHLY COST
    # --------------------------------------------------

    st.subheader("📈 Monthly Cost Trend")

    monthly_df = (
        df.assign(month=df["timestamp"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)
        .agg(total_cost=("cost", "sum"))
    )

    fig_monthly = px.line(
        monthly_df,
        x="month",
        y="total_cost",
        markers=True,
        title="Monthly Cloud Cost",
    )

    fig_monthly.update_layout(
        xaxis_title="Month",
        yaxis_title="Cost ($)",
    )

    st.plotly_chart(
        fig_monthly,
        width="stretch",
    )


    # --------------------------------------------------
    # TOP PROJECTS
    # --------------------------------------------------

    st.subheader("📊 Top Projects by Cost")

    project_df = (
        df.groupby("project", as_index=False)
        .agg(total_cost=("cost", "sum"))
        .sort_values("total_cost", ascending=False)
        .head(10)
    )

    fig_project = px.bar(
        project_df,
        x="total_cost",
        y="project",
        orientation="h",
        text_auto=".2s",
        title="Top 10 Projects by Cost",
    )

    fig_project.update_layout(
        xaxis_title="Cost ($)",
        yaxis_title="Project",
    )

    st.plotly_chart(
        fig_project,
        width="stretch",
    )


    # --------------------------------------------------
    # SERVICE ANALYSIS
    # --------------------------------------------------

    st.subheader("⚙️ Cost by Service")

    service_df = (
        df.groupby("service", as_index=False)
        .agg(total_cost=("cost", "sum"))
        .sort_values("total_cost", ascending=False)
    )

    fig_service = px.bar(
        service_df,
        x="service",
        y="total_cost",
        text_auto=".2s",
        title="Cost by Service",
    )

    fig_service.update_layout(
        xaxis_title="Service",
        yaxis_title="Cost ($)",
    )

    st.plotly_chart(
        fig_service,
        width="stretch",
    )


    # --------------------------------------------------


    # --------------------------------------------------
    # COST ANALYSIS INSIGHTS
    # --------------------------------------------------

    st.subheader("📌 Cost Analysis Insights")

    insight_total = df["cost"].sum()

    insight_provider = (
        df.groupby("cloud_provider")["cost"]
        .sum()
        .sort_values(ascending=False)
    )

    insight_project = (
        df.groupby("project")["cost"]
        .sum()
        .sort_values(ascending=False)
    )

    insight_service = (
        df.groupby("service")["cost"]
        .sum()
        .sort_values(ascending=False)
    )

    insight_monthly = (
        df.assign(month=df["timestamp"].dt.to_period("M"))
        .groupby("month")["cost"]
        .sum()
        .sort_index()
    )

    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:
        if not insight_provider.empty and insight_total > 0:
            top_provider = insight_provider.index[0]
            top_provider_cost = insight_provider.iloc[0]
            top_provider_share = top_provider_cost / insight_total * 100

            st.info(
                f"☁️ **Provider concentration:** {top_provider} contributes "
                f"**{top_provider_share:.1f}%** of total filtered spend "
                f"(${top_provider_cost:,.2f})."
            )

        if not insight_project.empty and insight_total > 0:
            top_project = insight_project.index[0]
            top_project_cost = insight_project.iloc[0]
            top_project_share = top_project_cost / insight_total * 100

            st.info(
                f"📊 **Project concentration:** {top_project} contributes "
                f"**{top_project_share:.1f}%** of filtered spend "
                f"(${top_project_cost:,.2f})."
            )

        if not insight_service.empty and insight_total > 0:
            top_service = insight_service.index[0]
            top_service_cost = insight_service.iloc[0]
            top_service_share = top_service_cost / insight_total * 100

            st.info(
                f"⚙️ **Service concentration:** {top_service} contributes "
                f"**{top_service_share:.1f}%** of filtered spend "
                f"(${top_service_cost:,.2f})."
            )

    with insight_col2:
        if len(insight_project) >= 3 and insight_total > 0:
            top3_cost = insight_project.head(3).sum()
            top3_share = top3_cost / insight_total * 100

            st.info(
                f"🏆 **Top 3 projects:** The three largest projects account "
                f"for **{top3_share:.1f}%** of filtered spend "
                f"(${top3_cost:,.2f})."
            )

        if len(insight_monthly) >= 2:
            latest_month = insight_monthly.iloc[-1]
            previous_month = insight_monthly.iloc[-2]

            if previous_month > 0:
                monthly_change = (
                    (latest_month - previous_month)
                    / previous_month
                    * 100
                )

                direction = (
                    "increased"
                    if monthly_change >= 0
                    else "decreased"
                )

                st.info(
                    f"📈 **Latest month:** Spend {direction} by "
                    f"**{abs(monthly_change):.1f}%** compared with "
                    f"the previous month."
                )

        if insight_total > 0:
            largest_project_value = (
                insight_project.iloc[0]
                if not insight_project.empty
                else 0
            )

            if largest_project_value / insight_total >= 0.10:
                st.warning(
                    "⚠️ **Concentration risk:** The highest-cost project "
                    "represents at least 10% of filtered cloud spend."
                )

    # --------------------------------------------------
    # COST OPTIMIZATION OPPORTUNITIES
    # --------------------------------------------------

    st.subheader("🎯 Cost Optimization Opportunities")

    optimization_actions = []

    if not insight_provider.empty:
        optimization_actions.append(
            f"Review {insight_provider.index[0]} because it has the "
            f"highest provider-level spend."
        )

    if not insight_project.empty:
        optimization_actions.append(
            f"Prioritize {insight_project.index[0]} for detailed "
            f"cost-driver investigation."
        )

    if not insight_service.empty:
        optimization_actions.append(
            f"Analyze {insight_service.index[0]} for pricing, utilization, "
            f"and workload optimization opportunities."
        )

    if high_cost_low_efficiency > 0:
        optimization_actions.append(
            f"Cross-check the {high_cost_low_efficiency:,} high-cost, "
            f"low-efficiency resources before making optimization decisions."
        )

    if over_budget_records > 0:
        optimization_actions.append(
            f"Review {over_budget_records:,} over-budget records as a "
            f"priority cost-control area."
        )

    for i, action in enumerate(optimization_actions[:5], start=1):
        st.write(f"**{i}.** {action}")


if dashboard_page == "🎯 Resource Efficiency":
    # RESOURCE EFFICIENCY
    # --------------------------------------------------

    st.subheader("🎯 Resource Efficiency")

    efficiency_df = (
        df.groupby("service", as_index=False)
        .agg(
            average_efficiency=(
                "utilization_efficiency_pct",
                "mean",
            ),
            total_cost=("cost", "sum"),
        )
        .sort_values("average_efficiency")
    )

    fig_efficiency = px.bar(
        efficiency_df,
        x="service",
        y="average_efficiency",
        text_auto=".1f",
        title="Average Utilization Efficiency by Service",
    )

    fig_efficiency.update_layout(
        xaxis_title="Service",
        yaxis_title="Efficiency (%)",
    )

    st.plotly_chart(
        fig_efficiency,
        width="stretch",
    )


    # --------------------------------------------------

    # --------------------------------------------------
    # EFFICIENCY INSIGHTS
    # --------------------------------------------------

    st.divider()

    st.subheader("📌 Efficiency Insights")

    total_resources_eff = df["resource_id"].nunique()

    low_efficiency_resources = df.loc[
        df["utilization_efficiency_pct"] < 30,
        "resource_id"
    ].nunique()

    high_cost_threshold = df["cost"].quantile(0.90)

    high_cost_low_eff_df = df[
        (df["cost"] >= high_cost_threshold)
        & (df["utilization_efficiency_pct"] < 30)
    ].copy()

    high_cost_low_eff_resources = (
        high_cost_low_eff_df["resource_id"].nunique()
    )

    low_efficiency_cost = high_cost_low_eff_df["cost"].sum()

    avg_efficiency = df["utilization_efficiency_pct"].mean()

    efficiency_col1, efficiency_col2, efficiency_col3, efficiency_col4 = st.columns(4)

    efficiency_col1.metric(
        "Average Efficiency",
        f"{avg_efficiency:.1f}%"
    )

    efficiency_col2.metric(
        "Total Resources",
        f"{total_resources_eff:,}"
    )

    efficiency_col3.metric(
        "Low-Efficiency Resources",
        f"{low_efficiency_resources:,}"
    )

    efficiency_col4.metric(
        "High-Cost + Low-Efficiency",
        f"{high_cost_low_eff_resources:,}"
    )

    st.caption(
        "High-cost resources are defined as resources in the top 10% "
        "of individual cost records. Low efficiency is below 30%."
    )

    # --------------------------------------------------
    # RESOURCE LEVEL ANALYSIS
    # --------------------------------------------------

    st.subheader("💸 High-Cost / Low-Efficiency Analysis")

    resource_efficiency_df = (
        df.groupby(
            [
                "resource_id",
                "service",
                "project",
                "department",
            ],
            as_index=False,
        )
        .agg(
            total_cost=("cost", "sum"),
            average_efficiency=(
                "utilization_efficiency_pct",
                "mean",
            ),
            average_cpu_utilization=(
                "cpu_utilization_pct",
                "mean",
            ),
            average_memory_utilization=(
                "memory_utilization_pct",
                "mean",
            ),
            average_storage_utilization=(
                "storage_utilization_pct",
                "mean",
            ),
            records=("usage_id", "count"),
        )
        .sort_values("total_cost", ascending=False)
    )

    inefficient_resources_df = resource_efficiency_df[
        resource_efficiency_df["average_efficiency"] < 30
    ].copy()

    inefficient_resources_df = inefficient_resources_df.head(20)

    if not inefficient_resources_df.empty:
        chart_df = inefficient_resources_df.sort_values(
            "total_cost",
            ascending=True,
        ).copy()

        fig_inefficient = px.bar(
            chart_df,
            x="total_cost",
            y="resource_id",
            orientation="h",
            text="total_cost",
            hover_data={
                "service": True,
                "project": True,
                "department": True,
                "average_efficiency": ":.1f",
                "average_cpu_utilization": ":.1f",
                "average_memory_utilization": ":.1f",
                "average_storage_utilization": ":.1f",
                "total_cost": ":,.2f",
            },
            title="Top High-Cost Resources with Efficiency Below 30%",
        )

        fig_inefficient.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
        )

        fig_inefficient.update_layout(
            height=650,
            xaxis_title="Total Cost ($)",
            yaxis_title="Resource",
            margin=dict(l=20, r=40, t=70, b=40),
        )

        st.plotly_chart(
            fig_inefficient,
            width="stretch",
        )

    # --------------------------------------------------
    # PROJECT EFFICIENCY
    # --------------------------------------------------

    st.subheader("📊 Efficiency by Project")

    project_efficiency_df = (
        df.groupby("project", as_index=False)
        .agg(
            average_efficiency=(
                "utilization_efficiency_pct",
                "mean",
            ),
            total_cost=("cost", "sum"),
            resources=("resource_id", "nunique"),
        )
        .sort_values("average_efficiency")
    )

    fig_project_eff = px.scatter(
        project_efficiency_df,
        x="average_efficiency",
        y="total_cost",
        size="resources",
        hover_name="project",
        text="project",
        title="Project Cost vs Average Utilization Efficiency",
    )

    fig_project_eff.update_traces(
        textposition="top center",
        marker=dict(
            sizemin=8,
            opacity=0.8,
        ),
    )

    fig_project_eff.update_layout(
        height=550,
        xaxis_title="Average Efficiency (%)",
        yaxis_title="Total Cost ($)",
        margin=dict(l=20, r=40, t=70, b=40),
    )

    st.plotly_chart(
        fig_project_eff,
        width="stretch",
    )

    # --------------------------------------------------
    # EFFICIENCY ACTIONS
    # --------------------------------------------------

    st.subheader("🎯 Efficiency Optimization Actions")

    efficiency_actions = []

    if high_cost_low_eff_resources > 0:
        efficiency_actions.append(
            f"Investigate {high_cost_low_eff_resources:,} high-cost resources "
            f"with efficiency below 30%."
        )

    if low_efficiency_cost > 0:
        efficiency_actions.append(
            f"Review ${low_efficiency_cost:,.2f} of spend associated with "
            f"high-cost, low-efficiency records."
        )

    if not inefficient_resources_df.empty:
        top_resource = inefficient_resources_df.iloc[0]["resource_id"]
        top_resource_cost = inefficient_resources_df.iloc[0]["total_cost"]

        efficiency_actions.append(
            f"Prioritize resource {top_resource}, which has "
            f"${top_resource_cost:,.2f} in aggregated cost among "
            f"low-efficiency resources."
        )

    if not project_efficiency_df.empty:
        least_efficient_project = project_efficiency_df.iloc[0]["project"]
        least_project_eff = project_efficiency_df.iloc[0]["average_efficiency"]

        efficiency_actions.append(
            f"Review {least_efficient_project}, which has the lowest "
            f"average project efficiency at {least_project_eff:.1f}%."
        )

    for i, action in enumerate(efficiency_actions[:5], start=1):
        st.write(f"**{i}.** {action}")


if dashboard_page == "🚨 Budget & Anomalies":
    # BUDGET ANALYSIS
    # --------------------------------------------------

    st.subheader("💰 Budget Analysis")

    budget_df = (
        df.groupby("project", as_index=False)
        .agg(
            budget_utilization=(
                "budget_utilization_pct",
                "mean",
            ),
            total_cost=("cost", "sum"),
        )
        .sort_values(
            "budget_utilization",
            ascending=False,
        )
    )

    fig_budget = px.bar(
        budget_df,
        x="project",
        y="budget_utilization",
        text_auto=".1f",
        title="Average Budget Utilization by Project",
    )

    fig_budget.add_hline(
        y=100,
        line_dash="dash",
        annotation_text="100% Budget Limit",
    )

    fig_budget.update_layout(
        xaxis_title="Project",
        yaxis_title="Budget Utilization (%)",
    )

    st.plotly_chart(
        fig_budget,
        width="stretch",
    )


    # --------------------------------------------------
    # REFRESH INFORMATION
    # --------------------------------------------------

    st.divider()

    st.caption(
        f"Last dashboard refresh: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    st.caption(
        "Data source: PostgreSQL → raw.cloudcost_billing"
    )


    # --------------------------------------------------
    # ANOMALY ANALYSIS
    # --------------------------------------------------

    st.divider()

    st.header("🚨 Budget & Anomaly Analysis")

    engine = get_connection()

    anomaly_query = """
        SELECT
            a.anomaly_category,
            a.usage_id,
            b.timestamp,
            b.cloud_provider,
            b.project,
            b.department,
            b.environment,
            b.region,
            b.service,
            b.owner_team,
            b.resource_id,
            b.cost
        FROM reference.anomaly_ground_truth a
        JOIN raw.cloudcost_billing b
            ON a.usage_id = b.usage_id
        WHERE b.timestamp::date BETWEEN :start_date AND :end_date
    """

    anomaly_params = {
        "start_date": start_date,
        "end_date": end_date,
    }

    anomaly_expanding = []

    anomaly_filters = {
        "cloud_provider": cloud_provider,
        "project": project,
        "department": department,
        "environment": environment,
        "region": region,
        "service": service,
        "owner_team": owner_team,
    }

    for column, values in anomaly_filters.items():
        if values:
            anomaly_query += f" AND b.{column} IN :{column}"
            anomaly_params[column] = values
            anomaly_expanding.append(column)

    anomaly_statement = text(anomaly_query)

    for parameter in anomaly_expanding:
        anomaly_statement = anomaly_statement.bindparams(
            bindparam(parameter, expanding=True)
        )

    with engine.connect() as conn:
        anomaly_df = pd.read_sql_query(
            anomaly_statement,
            conn,
            params=anomaly_params,
        )


    if anomaly_df.empty:

        st.info(
            "No anomalies found for the selected filters."
        )

    else:

        anomaly_count = len(anomaly_df)

        anomaly_types = anomaly_df[
            "anomaly_category"
        ].nunique()

        affected_resources = anomaly_df[
            "resource_id"
        ].nunique()

        anomaly_cost = anomaly_df["cost"].sum()

        # --------------------------------------------------
        # ANOMALY KPIs
        # --------------------------------------------------

        a1, a2, a3, a4 = st.columns(4)

        a1.metric(
            "Total Anomalies",
            f"{anomaly_count:,}",
        )

        a2.metric(
            "Anomaly Types",
            f"{anomaly_types:,}",
        )

        a3.metric(
            "Affected Resources",
            f"{affected_resources:,}",
        )

        a4.metric(
            "Anomaly Cost",
            f"${anomaly_cost:,.2f}",
        )

        # --------------------------------------------------
        # ANOMALIES BY TYPE
        # --------------------------------------------------

        st.subheader("🔎 Anomalies by Type")

        anomaly_type_df = (
            anomaly_df
            .groupby("anomaly_category", as_index=False)
            .agg(
                anomaly_count=("usage_id", "count"),
                anomaly_cost=("cost", "sum"),
                affected_resources=("resource_id", "nunique"),
            )
            .sort_values("anomaly_cost", ascending=True)
        )

        fig_anomaly_type = px.bar(
            anomaly_type_df,
            x="anomaly_cost",
            y="anomaly_category",
            orientation="h",
            text_auto=".2s",
            title="Anomaly Cost by Type",
        )

        fig_anomaly_type.update_layout(
            xaxis_title="Anomaly Cost ($)",
            yaxis_title="Anomaly Type",
        )

        st.plotly_chart(
            fig_anomaly_type,
            width="stretch",
        )

        # --------------------------------------------------
        # DAILY ANOMALY TREND
        # --------------------------------------------------

        st.subheader("📈 Daily Anomaly Trend")

        anomaly_daily_df = (
            anomaly_df
            .assign(
                anomaly_date=anomaly_df["timestamp"].dt.date
            )
            .groupby("anomaly_date", as_index=False)
            .agg(
                anomaly_count=("usage_id", "count"),
                anomaly_cost=("cost", "sum"),
            )
        )

        fig_anomaly_daily = px.line(
            anomaly_daily_df,
            x="anomaly_date",
            y="anomaly_count",
            markers=True,
            title="Daily Anomaly Count",
        )

        fig_anomaly_daily.update_layout(
            xaxis_title="Date",
            yaxis_title="Anomaly Count",
        )

        st.plotly_chart(
            fig_anomaly_daily,
            width="stretch",
        )

        # --------------------------------------------------
        # PROJECT IMPACT
        # --------------------------------------------------

        st.subheader("📁 Projects with Highest Anomaly Cost")

        anomaly_project_df = (
            anomaly_df
            .groupby("project", as_index=False)
            .agg(
                anomaly_count=("usage_id", "count"),
                anomaly_cost=("cost", "sum"),
                affected_resources=("resource_id", "nunique"),
            )
            .sort_values("anomaly_cost", ascending=True)
        )

        fig_anomaly_project = px.bar(
            anomaly_project_df,
            x="anomaly_cost",
            y="project",
            orientation="h",
            text_auto=".2s",
            title="Anomaly Cost by Project",
        )

        fig_anomaly_project.update_layout(
            xaxis_title="Anomaly Cost ($)",
            yaxis_title="Project",
        )

        st.plotly_chart(
            fig_anomaly_project,
            width="stretch",
        )

        # --------------------------------------------------
        # PROVIDER IMPACT
        # --------------------------------------------------

        st.subheader("☁️ Anomaly Impact by Cloud Provider")

        anomaly_provider_df = (
            anomaly_df
            .groupby("cloud_provider", as_index=False)
            .agg(
                anomaly_count=("usage_id", "count"),
                anomaly_cost=("cost", "sum"),
                affected_resources=("resource_id", "nunique"),
            )
            .sort_values("anomaly_cost", ascending=False)
        )

        fig_anomaly_provider = px.bar(
            anomaly_provider_df,
            x="cloud_provider",
            y="anomaly_cost",
            text_auto=".2s",
            title="Anomaly Cost by Cloud Provider",
        )

        fig_anomaly_provider.update_layout(
            xaxis_title="Cloud Provider",
            yaxis_title="Anomaly Cost ($)",
        )

        st.plotly_chart(
            fig_anomaly_provider,
            width="stretch",
        )

        # --------------------------------------------------
        # ANOMALY DETAILS
        # --------------------------------------------------

        st.subheader("📋 Anomaly Details")

        display_anomaly_df = (
            anomaly_type_df.copy()
        )

        display_anomaly_df["anomaly_cost"] = (
            display_anomaly_df["anomaly_cost"].round(2)
        )

        display_anomaly_df = display_anomaly_df.rename(
            columns={
                "anomaly_category": "Anomaly Type",
                "anomaly_count": "Count",
                "anomaly_cost": "Cost Impact",
                "affected_resources": "Resources",
            }
        )

        st.dataframe(
            display_anomaly_df,
            width="stretch",
            hide_index=True,
        )



        # --------------------------------------------------
        # ANOMALY INSIGHTS & MANAGEMENT ACTIONS
        # --------------------------------------------------

        st.divider()

        st.subheader("📌 Anomaly Insights")

        total_filtered_cost = df["cost"].sum()

        top_anomaly_type = (
            anomaly_type_df
            .sort_values("anomaly_cost", ascending=False)
            .iloc[0]
        )

        top_anomaly_project = (
            anomaly_project_df
            .sort_values("anomaly_cost", ascending=False)
            .iloc[0]
        )

        top_anomaly_provider = (
            anomaly_provider_df
            .sort_values("anomaly_cost", ascending=False)
            .iloc[0]
        )

        anomaly_cost_pct = (
            (anomaly_cost / total_filtered_cost) * 100
            if total_filtered_cost > 0
            else 0
        )

        insight_col1, insight_col2 = st.columns(2)

        with insight_col1:
            st.info(
                f"**Highest anomaly-cost type:** "
                f"{top_anomaly_type['anomaly_category']} — "
                f"${top_anomaly_type['anomaly_cost']:,.2f} "
                f"across {int(top_anomaly_type['anomaly_count']):,} records."
            )

            st.info(
                f"**Highest-impact project:** "
                f"{top_anomaly_project['project']} — "
                f"${top_anomaly_project['anomaly_cost']:,.2f} "
                f"across {int(top_anomaly_project['anomaly_count']):,} anomalies."
            )

        with insight_col2:
            st.info(
                f"**Highest-impact provider:** "
                f"{top_anomaly_provider['cloud_provider']} — "
                f"${top_anomaly_provider['anomaly_cost']:,.2f} "
                f"of anomaly cost."
            )

            st.info(
                f"**Anomaly cost exposure:** "
                f"${anomaly_cost:,.2f}, representing "
                f"{anomaly_cost_pct:.1f}% of filtered cloud spend."
            )

        # --------------------------------------------------
        # MANAGEMENT ACTIONS
        # --------------------------------------------------

        st.subheader("🎯 Recommended Management Actions")

        anomaly_actions = []

        anomaly_actions.append(
            f"Prioritize investigation of "
            f"{top_anomaly_type['anomaly_category']}, which has the "
            f"highest anomaly cost at "
            f"${top_anomaly_type['anomaly_cost']:,.2f}."
        )

        anomaly_actions.append(
            f"Review {top_anomaly_project['project']} first because it "
            f"has the highest anomaly cost at "
            f"${top_anomaly_project['anomaly_cost']:,.2f}."
        )

        anomaly_actions.append(
            f"Review {top_anomaly_provider['cloud_provider']} for "
            f"provider-level cost controls; it contributes "
            f"${top_anomaly_provider['anomaly_cost']:,.2f} "
            f"of anomaly cost."
        )

        if anomaly_cost_pct >= 5:
            anomaly_actions.append(
                f"Anomaly exposure is {anomaly_cost_pct:.1f}% of filtered "
                f"cloud spend, so remediation should be treated as a "
                f"priority cost-control activity."
            )
        else:
            anomaly_actions.append(
                f"Anomaly exposure is {anomaly_cost_pct:.1f}% of filtered "
                f"cloud spend; continue monitoring the highest-impact "
                f"categories and projects."
            )

        highest_daily_anomaly = (
            anomaly_daily_df
            .sort_values("anomaly_count", ascending=False)
            .iloc[0]
        )

        anomaly_actions.append(
            f"Investigate the peak anomaly date "
            f"{highest_daily_anomaly['anomaly_date']}, when "
            f"{int(highest_daily_anomaly['anomaly_count']):,} anomalies "
            f"were recorded."
        )

        for i, action in enumerate(anomaly_actions[:5], start=1):
            st.write(f"**{i}.** {action}")


if dashboard_page == "🤖 ML / Forecast Handoff":
    st.header("🤖 ML / Forecast Handoff")

    st.write(
        "Clean time-series dataset prepared for forecasting and ML."
    )

    # ----------------------------------------------
    # Continuous daily date index
    # ----------------------------------------------

    ml_daily = (
        df.assign(date=df["timestamp"].dt.floor("D"))
        .groupby("date", as_index=True)
        .agg(
            total_cost=("cost", "sum"),
            record_count=("usage_id", "count"),
            average_cost=("cost", "mean"),
        )
        .sort_index()
    )

    expected_dates = pd.date_range(
        start=pd.Timestamp(start_date),
        end=pd.Timestamp(end_date),
        freq="D",
    )

    ml_df = ml_daily.reindex(expected_dates)

    missing_dates = int(ml_df["record_count"].isna().sum())

    ml_df["total_cost"] = ml_df["total_cost"].fillna(0)
    ml_df["record_count"] = (
        ml_df["record_count"]
        .fillna(0)
        .astype(int)
    )
    ml_df["average_cost"] = ml_df["average_cost"].fillna(0)

    ml_df.index.name = "date"
    ml_df = ml_df.reset_index()

    st.subheader("📅 Daily Cost Time Series")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Daily Observations",
        f"{len(ml_df):,}",
    )

    col2.metric(
        "Missing Dates Filled",
        f"{missing_dates:,}",
    )

    col3.metric(
        "Total Cost",
        f"${ml_df['total_cost'].sum():,.2f}",
    )

    st.caption(
        "Missing dates are represented with zero cost and zero records "
        "so the forecasting date index remains continuous."
    )

    st.dataframe(
        ml_df,
        width="stretch",
        hide_index=True,
    )

    st.subheader("📈 Forecast Input")

    fig_ml = px.line(
        ml_df,
        x="date",
        y="total_cost",
        title="Daily Cloud Cost — ML Forecast Input",
    )

    fig_ml.update_layout(
        xaxis_title="Date",
        yaxis_title="Cost ($)",
    )

    st.plotly_chart(
        fig_ml,
        width="stretch",
    )

    csv_data = ml_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download Forecast-Ready CSV",
        data=csv_data,
        file_name="cloudpulse_forecast_input.csv",
        mime="text/csv",
        width="stretch",
    )


    # ----------------------------------------------
    # ML FEATURE ENGINEERING
    # ----------------------------------------------

    ml_df["rolling_7d_cost"] = (
        ml_df["total_cost"]
        .rolling(window=7, min_periods=1)
        .mean()
    )

    ml_df["daily_cost_change_pct"] = (
        ml_df["total_cost"]
        .pct_change()
        .replace([float("inf"), float("-inf")], 0)
        .fillna(0)
        * 100
    )

    ml_df["day_of_week"] = ml_df["date"].dt.dayofweek
    ml_df["month"] = ml_df["date"].dt.month
    ml_df["is_weekend"] = (
        ml_df["date"].dt.dayofweek >= 5
    ).astype(int)

    # ----------------------------------------------
    # ML DATASET QUALITY
    # ----------------------------------------------

    st.subheader("🧪 ML Dataset Quality")

    ml_quality_col1, ml_quality_col2, ml_quality_col3, ml_quality_col4 = st.columns(4)

    volatility = ml_df["total_cost"].std()

    high_cost_threshold = ml_df["total_cost"].quantile(0.90)

    high_cost_days = int(
        (ml_df["total_cost"] >= high_cost_threshold).sum()
    )

    max_cost_day = ml_df.loc[
        ml_df["total_cost"].idxmax()
    ]

    ml_quality_col1.metric(
        "Cost Volatility",
        f"${volatility:,.2f}"
    )

    ml_quality_col2.metric(
        "High-Cost Days",
        f"{high_cost_days:,}"
    )

    ml_quality_col3.metric(
        "Peak Daily Cost",
        f"${ml_df['total_cost'].max():,.2f}"
    )

    ml_quality_col4.metric(
        "Avg Daily Cost",
        f"${ml_df['total_cost'].mean():,.2f}"
    )

    st.caption(
        "High-cost days are defined as days at or above the "
        "90th percentile of daily cloud cost."
    )

    # ----------------------------------------------
    # ROLLING COST TREND
    # ----------------------------------------------

    st.subheader("📊 Daily Cost & 7-Day Rolling Average")

    fig_rolling = px.line(
        ml_df,
        x="date",
        y=["total_cost", "rolling_7d_cost"],
        title="Daily Cloud Cost vs 7-Day Rolling Average",
    )

    fig_rolling.update_layout(
        xaxis_title="Date",
        yaxis_title="Cost ($)",
        legend_title="Metric",
    )

    st.plotly_chart(
        fig_rolling,
        width="stretch",
    )

    # ----------------------------------------------
    # DAILY COST GROWTH
    # ----------------------------------------------

    st.subheader("📈 Daily Cost Growth")

    fig_growth = px.line(
        ml_df,
        x="date",
        y="daily_cost_change_pct",
        title="Daily Cost Change (%)",
    )

    fig_growth.add_hline(
        y=0,
        line_dash="dash",
    )

    fig_growth.update_layout(
        xaxis_title="Date",
        yaxis_title="Daily Change (%)",
    )

    st.plotly_chart(
        fig_growth,
        width="stretch",
    )

    # ----------------------------------------------
    # ML FEATURE PREVIEW
    # ----------------------------------------------

    st.subheader("🧠 ML Feature Preview")

    ml_feature_columns = [
        "date",
        "total_cost",
        "record_count",
        "average_cost",
        "rolling_7d_cost",
        "daily_cost_change_pct",
        "day_of_week",
        "month",
        "is_weekend",
    ]

    st.dataframe(
        ml_df[ml_feature_columns].tail(30),
        width="stretch",
        hide_index=True,
    )

    # ----------------------------------------------
    # ML INSIGHTS & ACTIONS
    # ----------------------------------------------

    st.subheader("📌 ML Handoff Insights")

    ml_actions = []

    ml_actions.append(
        f"Peak daily cost was ${max_cost_day['total_cost']:,.2f} "
        f"on {max_cost_day['date'].date()}."
    )

    ml_actions.append(
        f"The daily cost series contains {len(ml_df):,} observations "
        f"with {missing_dates:,} filled dates."
    )

    ml_actions.append(
        f"The average daily cloud cost is "
        f"${ml_df['total_cost'].mean():,.2f}, with cost volatility "
        f"of ${volatility:,.2f}."
    )

    latest_growth = ml_df.iloc[-1]["daily_cost_change_pct"]

    if latest_growth > 0:
        ml_actions.append(
            f"The latest day shows a {latest_growth:.1f}% increase "
            f"in cost versus the previous day."
        )
    elif latest_growth < 0:
        ml_actions.append(
            f"The latest day shows a {abs(latest_growth):.1f}% decrease "
            f"in cost versus the previous day."
        )
    else:
        ml_actions.append(
            "The latest day shows no change versus the previous day."
        )

    ml_actions.append(
        f"{high_cost_days:,} days are classified as high-cost days "
        f"using the 90th percentile threshold."
    )

    for i, action in enumerate(ml_actions[:5], start=1):
        st.write(f"**{i}.** {action}")

    st.subheader("📋 ML Handoff Summary")

    st.write(
        f"The selected filters produce **{len(ml_df):,} daily observations** "
        f"from **{start_date}** to **{end_date}**. "
        f"The daily index is continuous and contains "
        f"**{missing_dates:,} filled date(s)**."
    )

    st.success(
        "ML handoff ready: continuous daily index, explicit missing-date "
        "policy, daily cost target, record count, and average daily cost."
    )
