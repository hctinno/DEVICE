PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS blobs(sha256 TEXT PRIMARY KEY,bytes INTEGER NOT NULL,kind TEXT NOT NULL,synthetic INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS packages(package_id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,summary_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(document_id TEXT PRIMARY KEY,package_id TEXT NOT NULL REFERENCES packages,
 sha256 TEXT REFERENCES blobs,record_json TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'unreviewed',synthetic INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cases(case_id TEXT PRIMARY KEY,data_json TEXT NOT NULL,synthetic INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS methods(method_id TEXT PRIMARY KEY,data_json TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'unreviewed');
CREATE TABLE IF NOT EXISTS plans(plan_id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases,method_id TEXT NOT NULL REFERENCES methods,data_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES plans,raw_sha256 TEXT REFERENCES blobs,data_json TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'unreviewed');
CREATE TABLE IF NOT EXISTS evaluations(evaluation_id INTEGER PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs,fingerprint TEXT NOT NULL,data_json TEXT NOT NULL,UNIQUE(run_id,fingerprint));
CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY,created_at TEXT NOT NULL,action TEXT NOT NULL,subject_id TEXT NOT NULL,details_json TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS intake_sources(
 source_id TEXT PRIMARY KEY, root TEXT NOT NULL UNIQUE, synthetic INTEGER NOT NULL,
 settle_seconds REAL NOT NULL CHECK(settle_seconds>0));
CREATE TABLE IF NOT EXISTS intakes(
 intake_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES intake_sources,
 bundle TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
 delegated INTEGER NOT NULL DEFAULT 0, deferred INTEGER NOT NULL DEFAULT 0,
 analysis_json TEXT, UNIQUE(source_id,bundle));
CREATE TABLE IF NOT EXISTS intake_observations(
 source_id TEXT NOT NULL REFERENCES intake_sources, bundle TEXT NOT NULL,
 fingerprint TEXT NOT NULL, stable_since REAL NOT NULL, PRIMARY KEY(source_id,bundle));
CREATE TABLE IF NOT EXISTS intake_revisions(
 intake_id TEXT NOT NULL REFERENCES intakes, revision INTEGER NOT NULL,
 fingerprint TEXT NOT NULL, files_json TEXT NOT NULL, synthetic INTEGER NOT NULL,
 created_at REAL NOT NULL, PRIMARY KEY(intake_id,revision));
CREATE TABLE IF NOT EXISTS intake_jobs(
 job_id TEXT PRIMARY KEY, intake_id TEXT NOT NULL, revision INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','running','completed','failed','superseded')),
 worker_id TEXT, token TEXT, lease_until REAL, attempt INTEGER NOT NULL DEFAULT 0,
 result_json TEXT, error_code TEXT, created_at REAL NOT NULL,
 UNIQUE(intake_id,revision),
 FOREIGN KEY(intake_id,revision) REFERENCES intake_revisions(intake_id,revision));
CREATE TABLE IF NOT EXISTS intake_questions(
 intake_id TEXT NOT NULL REFERENCES intakes, question_key TEXT NOT NULL,
 question_json TEXT NOT NULL, state TEXT NOT NULL, last_revision INTEGER NOT NULL,
 PRIMARY KEY(intake_id,question_key));
CREATE TABLE IF NOT EXISTS intake_answers(
 intake_id TEXT NOT NULL REFERENCES intakes, field TEXT NOT NULL, value TEXT NOT NULL,
 basis_json TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(intake_id,field));
CREATE TABLE IF NOT EXISTS intake_responses(
 event_id TEXT PRIMARY KEY, request_json TEXT NOT NULL, result_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS intake_notifications(
 notification_id INTEGER PRIMARY KEY, intake_id TEXT NOT NULL REFERENCES intakes,
 revision INTEGER NOT NULL, signature TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS intake_notice_state(
 intake_id TEXT PRIMARY KEY REFERENCES intakes, signature TEXT NOT NULL);
