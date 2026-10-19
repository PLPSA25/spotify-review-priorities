-- Run as the database owner AFTER the schema/import, never as app runtime.
-- No password here: Pier sets it privately in the Neon console after this script.
-- PUBLIC revocations affect every database user relying on those public grants.
-- PostgreSQL system catalogs remain readable; this is an application-data boundary.
BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dashboard_reader') THEN
    CREATE ROLE dashboard_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
      NOINHERIT NOREPLICATION NOBYPASSRLS;
  END IF;
  IF EXISTS (
    SELECT FROM pg_auth_members m
    JOIN pg_roles r ON r.oid = m.member
    WHERE r.rolname = 'dashboard_reader'
  ) THEN
    RAISE EXCEPTION 'dashboard_reader has role memberships; review/remove them before continuing';
  END IF;
  IF EXISTS (
    SELECT FROM pg_shdepend d
    JOIN pg_roles r ON r.oid = d.refobjid
    WHERE r.rolname = 'dashboard_reader' AND d.deptype = 'o'
  ) THEN
    RAISE EXCEPTION 'dashboard_reader owns objects; use a separate owner before continuing';
  END IF;
END $$;

ALTER ROLE dashboard_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOINHERIT NOREPLICATION NOBYPASSRLS;

DO $$
DECLARE s record;
BEGIN
  -- PUBLIC database CREATE/TEMP would otherwise bypass direct role revocations.
  EXECUTE format('REVOKE CREATE, TEMPORARY ON DATABASE %I FROM PUBLIC', current_database());
  EXECUTE format('REVOKE ALL ON DATABASE %I FROM dashboard_reader', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO dashboard_reader', current_database());
  FOR s IN SELECT nspname FROM pg_namespace
    WHERE nspname <> 'information_schema' AND nspname !~ '^pg_'
  LOOP
    EXECUTE format('REVOKE ALL ON SCHEMA %I FROM dashboard_reader', s.nspname);
    EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA %I FROM dashboard_reader', s.nspname);
    EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA %I FROM dashboard_reader', s.nspname);
    EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA %I FROM dashboard_reader', s.nspname);
  END LOOP;
END $$;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA dashboard FROM PUBLIC;
REVOKE ALL ON TABLE dashboard.snapshots FROM PUBLIC;
GRANT USAGE ON SCHEMA dashboard TO dashboard_reader;
GRANT SELECT ON TABLE dashboard.snapshots TO dashboard_reader;
ALTER ROLE dashboard_reader SET default_transaction_read_only = on;
ALTER ROLE dashboard_reader SET statement_timeout = '5s';

-- Fail closed if an existing PUBLIC schema grant still exposes another
-- application schema. Do not silently modify unrelated schemas' PUBLIC grants.
DO $$
BEGIN
  IF EXISTS (
    SELECT FROM pg_namespace
    WHERE nspname <> 'dashboard' AND nspname <> 'information_schema'
      AND nspname !~ '^pg_'
      AND (has_schema_privilege('dashboard_reader', oid, 'USAGE')
        OR has_schema_privilege('dashboard_reader', oid, 'CREATE'))
  ) THEN
    RAISE EXCEPTION 'Other application schemas remain accessible through PUBLIC; owner review required';
  END IF;
  IF has_table_privilege('dashboard_reader', 'dashboard.snapshots',
    'INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER') OR EXISTS (
    SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'dashboard' AND c.relname <> 'snapshots'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
      AND has_table_privilege('dashboard_reader', c.oid,
        'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')
  ) THEN
    RAISE EXCEPTION 'Unexpected effective table privileges; owner review required';
  END IF;
END $$;
COMMIT;

-- Grants are the real boundary. Read-only default and timeout are secondary;
-- the reader can change its own session defaults, but cannot grant privileges.
