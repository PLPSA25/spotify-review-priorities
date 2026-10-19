-- Run as the database/schema/table owner AFTER the schema/import.
-- If a previous attempt aborted an open transaction, issue ROLLBACK first.
-- No password here: Pier sets it privately in the Neon console.
-- PUBLIC revocations affect other users relying on those grants.
-- System catalogs remain readable; this is an application-data boundary.
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
    RAISE EXCEPTION 'dashboard_reader has role memberships; owner review required';
  END IF;
  IF EXISTS (
    SELECT FROM pg_shdepend d
    JOIN pg_roles r ON r.oid = d.refobjid
    WHERE r.rolname = 'dashboard_reader' AND d.deptype = 'o'
  ) THEN
    RAISE EXCEPTION 'dashboard_reader owns objects; owner review required';
  END IF;
END $$;

-- Inspect attributes instead of attempting privileged attribute changes.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_roles WHERE rolname = 'dashboard_reader'
      AND rolcanlogin AND NOT rolsuper AND NOT rolcreaterole
      AND NOT rolcreatedb AND NOT rolbypassrls AND NOT rolreplication
      AND NOT rolinherit
  ) THEN
    RAISE EXCEPTION 'dashboard_reader has unsafe role attributes; owner review required';
  END IF;
END $$;

DO $$
BEGIN
  EXECUTE format('REVOKE CREATE, TEMPORARY ON DATABASE %I FROM PUBLIC', current_database());
  EXECUTE format('REVOKE ALL ON DATABASE %I FROM dashboard_reader', current_database());
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO dashboard_reader', current_database());
END $$;

-- Touch only the intended application objects and the public schema.
-- Do not sweep Neon-managed or unrelated schemas/tables/functions.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM dashboard_reader;
REVOKE ALL ON SCHEMA dashboard FROM PUBLIC, dashboard_reader;
REVOKE ALL ON TABLE dashboard.snapshots FROM PUBLIC, dashboard_reader;
GRANT USAGE ON SCHEMA dashboard TO dashboard_reader;
GRANT SELECT ON TABLE dashboard.snapshots TO dashboard_reader;

-- These settings require authority to alter this ordinary role's defaults.
ALTER ROLE dashboard_reader SET default_transaction_read_only = on;
ALTER ROLE dashboard_reader SET statement_timeout = '5s';

-- REVOKE/GRANT can warn without changing every requested privilege. Check
-- effective privileges explicitly before COMMIT; never accept warnings as proof.
DO $$
BEGIN
  IF NOT has_database_privilege('dashboard_reader', current_database(), 'CONNECT')
    OR has_database_privilege('dashboard_reader', current_database(), 'CREATE')
    OR has_database_privilege('dashboard_reader', current_database(), 'TEMPORARY')
    OR NOT has_schema_privilege('dashboard_reader', 'dashboard', 'USAGE')
    OR has_schema_privilege('dashboard_reader', 'dashboard', 'CREATE')
    OR NOT has_table_privilege('dashboard_reader', 'dashboard.snapshots', 'SELECT')
  THEN
    RAISE EXCEPTION 'Required CONNECT/USAGE/SELECT or CREATE/TEMP denial failed';
  END IF;
  IF EXISTS (
    SELECT FROM pg_namespace
    WHERE nspname <> 'dashboard' AND nspname <> 'information_schema'
      AND nspname !~ '^pg_'
      AND (has_schema_privilege('dashboard_reader', oid, 'USAGE')
        OR has_schema_privilege('dashboard_reader', oid, 'CREATE'))
  ) THEN
    RAISE EXCEPTION 'Other application schemas remain accessible; owner review required';
  END IF;
  IF has_table_privilege('dashboard_reader', 'dashboard.snapshots',
    'INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')
    OR has_any_column_privilege('dashboard_reader', 'dashboard.snapshots',
      'INSERT, UPDATE, REFERENCES')
    OR EXISTS (
      SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'dashboard' AND c.relname <> 'snapshots'
        AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
        AND (has_table_privilege('dashboard_reader', c.oid,
          'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')
          OR has_any_column_privilege('dashboard_reader', c.oid,
            'SELECT, INSERT, UPDATE, REFERENCES'))
    )
  THEN
    RAISE EXCEPTION 'Unexpected effective table/column privileges; owner review required';
  END IF;
END $$;
COMMIT;

-- Grants are the real boundary. Read-only default and timeout are secondary;
-- the reader can change its own session defaults, but cannot grant privileges.
