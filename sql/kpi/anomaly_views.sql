CREATE OR REPLACE VIEW analytics.v_anomaly_summary AS
SELECT
    COUNT(*) AS anomaly_count,
    COUNT(DISTINCT a.anomaly_category) AS anomaly_types,
    COUNT(DISTINCT b.resource_id) AS affected_resources,
    COUNT(DISTINCT b.project) AS affected_projects,
    COALESCE(SUM(b.cost), 0) AS anomaly_cost
FROM reference.anomaly_ground_truth a
JOIN raw.cloudcost_billing b
    ON a.usage_id = b.usage_id;


CREATE OR REPLACE VIEW analytics.v_anomaly_by_type AS
SELECT
    a.anomaly_category,
    COUNT(*) AS anomaly_count,
    COALESCE(SUM(b.cost), 0) AS anomaly_cost,
    COUNT(DISTINCT b.resource_id) AS affected_resources,
    COUNT(DISTINCT b.project) AS affected_projects
FROM reference.anomaly_ground_truth a
JOIN raw.cloudcost_billing b
    ON a.usage_id = b.usage_id
GROUP BY a.anomaly_category
ORDER BY anomaly_count DESC;


CREATE OR REPLACE VIEW analytics.v_anomaly_by_project AS
SELECT
    b.project,
    COUNT(*) AS anomaly_count,
    COALESCE(SUM(b.cost), 0) AS anomaly_cost,
    COUNT(DISTINCT b.resource_id) AS affected_resources
FROM reference.anomaly_ground_truth a
JOIN raw.cloudcost_billing b
    ON a.usage_id = b.usage_id
GROUP BY b.project
ORDER BY anomaly_cost DESC;


CREATE OR REPLACE VIEW analytics.v_anomaly_by_provider AS
SELECT
    b.cloud_provider,
    COUNT(*) AS anomaly_count,
    COALESCE(SUM(b.cost), 0) AS anomaly_cost,
    COUNT(DISTINCT b.resource_id) AS affected_resources
FROM reference.anomaly_ground_truth a
JOIN raw.cloudcost_billing b
    ON a.usage_id = b.usage_id
GROUP BY b.cloud_provider
ORDER BY anomaly_cost DESC;


CREATE OR REPLACE VIEW analytics.v_anomaly_daily AS
SELECT
    b.timestamp::date AS anomaly_date,
    COUNT(*) AS anomaly_count,
    COALESCE(SUM(b.cost), 0) AS anomaly_cost
FROM reference.anomaly_ground_truth a
JOIN raw.cloudcost_billing b
    ON a.usage_id = b.usage_id
GROUP BY b.timestamp::date
ORDER BY anomaly_date;
