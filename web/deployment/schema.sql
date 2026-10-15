CREATE SCHEMA IF NOT EXISTS dashboard;
REVOKE ALL ON SCHEMA dashboard FROM PUBLIC;
CREATE TABLE IF NOT EXISTS dashboard.snapshots (
  snapshot_id text PRIMARY KEY CHECK (snapshot_id ~ '^[a-f0-9]{64}$'),
  payload jsonb NOT NULL CHECK (payload ->> 'snapshot_id' = snapshot_id),
  imported_at timestamptz NOT NULL DEFAULT now(),
  published boolean NOT NULL DEFAULT false
);
REVOKE ALL ON dashboard.snapshots FROM PUBLIC;
