-- Run as the owner later. SQL creation avoids neon_superuser membership.
-- NOLOGIN is intentional until the owner privately provisions its password.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dashboard_reader') THEN
    CREATE ROLE dashboard_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;
DO $$ BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO dashboard_reader', current_database());
END $$;
GRANT USAGE ON SCHEMA dashboard TO dashboard_reader;
GRANT SELECT ON dashboard.snapshots TO dashboard_reader;
ALTER ROLE dashboard_reader SET default_transaction_read_only = on;
ALTER ROLE dashboard_reader SET statement_timeout = '10s';
-- Owner: privately set LOGIN + password later; never store it in this file.
-- Do not place an owner/import URL or reader password in this SQL file.
