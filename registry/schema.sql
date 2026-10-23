PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE source_documents (
    source_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    imported_at TEXT NOT NULL,
    source_path TEXT NOT NULL,
    sheet_count INTEGER NOT NULL,
    record_count INTEGER NOT NULL
);
CREATE TABLE source_sheets (
    source_id TEXT NOT NULL REFERENCES source_documents,
    sheet_name TEXT NOT NULL,
    header_row INTEGER NOT NULL,
    headers_json TEXT NOT NULL CHECK(json_valid(headers_json)),
    title TEXT,
    visibility TEXT NOT NULL,
    PRIMARY KEY(source_id, sheet_name)
);
CREATE TABLE source_rows (
    source_row_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    row_number INTEGER NOT NULL,
    cells_json TEXT NOT NULL CHECK(json_valid(cells_json)),
    UNIQUE(source_id, sheet_name, row_number),
    FOREIGN KEY(source_id, sheet_name) REFERENCES source_sheets
);
CREATE TABLE manufacturers (
    manufacturer_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    name_key TEXT NOT NULL UNIQUE,
    verification_status TEXT NOT NULL DEFAULT 'source_only'
      CHECK(verification_status IN ('source_only','verified'))
);
CREATE TABLE manufacturer_aliases (
    raw_label TEXT PRIMARY KEY,
    manufacturer_id TEXT REFERENCES manufacturers,
    normalization_method TEXT NOT NULL,
    review_required INTEGER NOT NULL CHECK(review_required IN (0,1)),
    suggested_canonical_name TEXT,
    rationale TEXT NOT NULL
);
CREATE TABLE categories (
    category_id TEXT PRIMARY KEY,
    domain_ko TEXT NOT NULL,
    category_ko TEXT NOT NULL,
    automation_research_hint TEXT NOT NULL,
    rule_pattern TEXT NOT NULL
);
CREATE TABLE models (
    model_id TEXT PRIMARY KEY,
    manufacturer_id TEXT NOT NULL REFERENCES manufacturers,
    model_name TEXT NOT NULL,
    model_key TEXT NOT NULL,
    UNIQUE(manufacturer_id, model_key),
    UNIQUE(model_id, manufacturer_id)
);
CREATE TABLE equipment (
    equipment_id TEXT PRIMARY KEY,
    source_row_id TEXT NOT NULL UNIQUE REFERENCES source_rows,
    register_no INTEGER NOT NULL,
    name TEXT,
    manufacturer_id TEXT REFERENCES manufacturers,
    model_id TEXT REFERENCES models,
    model_name TEXT,
    serial_number TEXT,
    specification TEXT,
    calibration_specification TEXT,
    note TEXT,
    firmware TEXT,
    category_id TEXT NOT NULL REFERENCES categories,
    classification_status TEXT NOT NULL CHECK(classification_status IN ('suggested','unclassified','reviewed')),
    classification_rule TEXT NOT NULL,
    source_status_hint TEXT NOT NULL DEFAULT 'no_status_evidence',
    lifecycle_status TEXT NOT NULL DEFAULT 'unknown'
      CHECK(lifecycle_status IN ('unknown','in_service','out_of_service','retired')),
    automation_status TEXT NOT NULL DEFAULT 'not_assessed'
      CHECK(automation_status IN ('not_assessed','researching','documented','bench_verified','production_ready','not_applicable')),
    location TEXT,
    owner TEXT,
    calibration_due_date TEXT,
    CHECK(model_id IS NULL OR manufacturer_id IS NOT NULL),
    FOREIGN KEY(model_id, manufacturer_id) REFERENCES models(model_id, manufacturer_id)
);
CREATE INDEX equipment_manufacturer_idx ON equipment(manufacturer_id);
CREATE INDEX equipment_model_idx ON equipment(model_id);
CREATE INDEX equipment_category_idx ON equipment(category_id);
CREATE INDEX equipment_serial_idx ON equipment(serial_number);
CREATE INDEX equipment_register_idx ON equipment(register_no);

CREATE TABLE equipment_identifiers (
    identifier_id INTEGER PRIMARY KEY,
    equipment_id TEXT NOT NULL REFERENCES equipment,
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    source_field TEXT NOT NULL,
    source_excerpt TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'source_extracted'
);
CREATE INDEX equipment_identifiers_value_idx ON equipment_identifiers(identifier_value);

-- Model-level documentation and drivers; source data does not establish support.
CREATE TABLE model_automation_profiles (
    model_id TEXT PRIMARY KEY REFERENCES models,
    research_status TEXT NOT NULL DEFAULT 'not_assessed'
      CHECK(research_status IN ('not_assessed','researching','documented','bench_verified','not_applicable')),
    remote_control_supported INTEGER CHECK(remote_control_supported IN (0,1)),
    manual_url TEXT,
    programming_manual_url TEXT,
    sdk_url TEXT,
    driver_key TEXT,
    notes TEXT,
    verified_at TEXT
);
CREATE TABLE model_interfaces (
    interface_id INTEGER PRIMARY KEY,
    model_id TEXT NOT NULL REFERENCES models,
    transport TEXT NOT NULL,
    protocol TEXT,
    evidence_reference TEXT NOT NULL,
    verification_status TEXT NOT NULL CHECK(verification_status IN ('documented','bench_verified')),
    notes TEXT
);
-- Unit-specific endpoints, deliberately empty until the actual unit is inspected.
CREATE TABLE equipment_connections (
    connection_id INTEGER PRIMARY KEY,
    equipment_id TEXT NOT NULL REFERENCES equipment,
    transport TEXT NOT NULL,
    resource_address TEXT NOT NULL,
    protocol TEXT,
    settings_json TEXT CHECK(settings_json IS NULL OR json_valid(settings_json)),
    verification_status TEXT NOT NULL DEFAULT 'unverified'
      CHECK(verification_status IN ('unverified','bench_verified')),
    last_identity_response TEXT,
    verified_at TEXT,
    UNIQUE(equipment_id, transport, resource_address)
);
CREATE TABLE data_quality_issues (
    issue_id INTEGER PRIMARY KEY,
    equipment_id TEXT NOT NULL REFERENCES equipment,
    field_name TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('high','medium','low')),
    detail TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'open'
      CHECK(review_status IN ('open','resolved','accepted'))
);
CREATE INDEX quality_equipment_idx ON data_quality_issues(equipment_id);
CREATE TABLE duplicate_groups (
    duplicate_group_id TEXT PRIMARY KEY,
    match_type TEXT NOT NULL,
    match_key_json TEXT NOT NULL CHECK(json_valid(match_key_json)),
    member_count INTEGER NOT NULL CHECK(member_count > 1),
    resolution_status TEXT NOT NULL DEFAULT 'unreviewed'
);
CREATE TABLE duplicate_members (
    duplicate_group_id TEXT NOT NULL REFERENCES duplicate_groups,
    equipment_id TEXT NOT NULL REFERENCES equipment,
    PRIMARY KEY(duplicate_group_id, equipment_id)
);

CREATE VIEW v_equipment_inventory AS
SELECT e.equipment_id, e.register_no, e.name,
       m.canonical_name AS manufacturer, e.model_name, e.serial_number,
       c.domain_ko AS domain, c.category_ko AS category,
       e.specification, e.calibration_specification, e.note, e.firmware,
       e.classification_status, e.classification_rule,
       c.automation_research_hint, e.automation_status,
       e.lifecycle_status, e.source_status_hint, e.location, e.owner, e.calibration_due_date,
       e.manufacturer_id, e.model_id,
       json_extract(r.cells_json,'$[2]') AS manufacturer_raw,
       json_extract(r.cells_json,'$[1]') AS name_raw,
       json_extract(r.cells_json,'$[3]') AS model_raw,
       json_extract(r.cells_json,'$[4]') AS serial_raw,
       json_extract(r.cells_json,'$[5]') AS specification_raw,
       json_extract(r.cells_json,'$[6]') AS calibration_specification_raw,
       json_extract(r.cells_json,'$[7]') AS note_raw,
       json_extract(r.cells_json,'$[8]') AS firmware_raw,
       r.sheet_name, r.row_number AS source_row,
       d.original_filename, d.sha256 AS source_sha256
FROM equipment e
JOIN source_rows r USING(source_row_id)
JOIN source_documents d USING(source_id)
LEFT JOIN manufacturers m USING(manufacturer_id)
JOIN categories c USING(category_id);

CREATE VIEW v_manufacturer_summary AS
SELECT m.manufacturer_id, m.canonical_name AS manufacturer,
       COUNT(e.equipment_id) AS equipment_records,
       COUNT(DISTINCT e.model_id) AS model_count,
       (SELECT COUNT(*) FROM manufacturer_aliases a WHERE a.manufacturer_id=m.manufacturer_id) AS source_label_count,
       m.verification_status
FROM manufacturers m LEFT JOIN equipment e USING(manufacturer_id)
GROUP BY m.manufacturer_id;

CREATE VIEW v_model_research_queue AS
SELECT mo.model_id, ma.canonical_name AS manufacturer, mo.model_name,
       COUNT(e.equipment_id) AS equipment_records,
       GROUP_CONCAT(DISTINCT c.category_ko) AS suggested_categories,
       GROUP_CONCAT(DISTINCT c.automation_research_hint) AS research_hints,
       p.research_status, p.remote_control_supported, p.manual_url,
       p.programming_manual_url, p.sdk_url, p.driver_key, p.notes, p.verified_at
FROM models mo JOIN manufacturers ma USING(manufacturer_id)
JOIN equipment e USING(model_id)
JOIN categories c USING(category_id)
JOIN model_automation_profiles p USING(model_id)
GROUP BY mo.model_id;
