CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    name TEXT NOT NULL,
    sector_group TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS company_metrics (
    company_id TEXT NOT NULL,
    fiscal_period TEXT NOT NULL,
    revenue DOUBLE,
    cash DOUBLE,
    debt DOUBLE,
    operating_income DOUBLE,
    capital_expenditure DOUBLE,
    interest_expense DOUBLE,
    metric_source_ids TEXT,
    PRIMARY KEY (company_id, fiscal_period)
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_date DATE,
    url TEXT NOT NULL,
    local_path TEXT,
    extraction_status TEXT NOT NULL,
    retrieved_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    parser_method TEXT NOT NULL,
    confidence DOUBLE NOT NULL,
    source_location TEXT
);

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    buyer_company_id TEXT NOT NULL,
    seller_company_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    annual_flow_low DOUBLE,
    annual_flow_base DOUBLE NOT NULL,
    annual_flow_high DOUBLE,
    dependency_percentage DOUBLE,
    confidence_score DOUBLE NOT NULL,
    evidence_item_ids TEXT NOT NULL,
    estimation_method TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS scenario_runs (
    scenario_id TEXT PRIMARY KEY,
    shock_source_group TEXT NOT NULL,
    shock_percentage DOUBLE NOT NULL,
    pass_through_rate DOUBLE NOT NULL,
    propagation_factor DOUBLE NOT NULL,
    max_rounds INTEGER NOT NULL,
    estimate_mode TEXT NOT NULL,
    run_timestamp TIMESTAMP NOT NULL,
    per_company_impacts TEXT NOT NULL,
    per_edge_pulses TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relationship_candidates (
    candidate_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    candidate_json TEXT NOT NULL,
    verification_json TEXT NOT NULL,
    mechanically_valid BOOLEAN NOT NULL,
    saved_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_audit_log (
    audit_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    verification_valid BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL
);
