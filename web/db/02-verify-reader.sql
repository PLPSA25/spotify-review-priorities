-- Run in a NEW connection authenticated AS dashboard_reader, not as the owner.
-- Use the Neon SQL editor's role selector only if it authenticates as that role;
-- otherwise use an existing SQL client privately. Never print a connection URL.
-- Execute as a complete script; preserve the final ROLLBACK.
SELECT current_user, session_user;
SELECT rolname, rolcanlogin, rolsuper, rolcreaterole, rolcreatedb,
       rolbypassrls, rolreplication, rolinherit
FROM pg_roles WHERE rolname = current_user;

WITH RECURSIVE memberships(roleid) AS (
  SELECT roleid FROM pg_auth_members
  WHERE member = (SELECT oid FROM pg_roles WHERE rolname = current_user)
  UNION
  SELECT m.roleid FROM pg_auth_members m
  JOIN memberships inherited ON m.member = inherited.roleid
)
SELECT r.rolname AS direct_or_transitive_membership
FROM memberships m JOIN pg_roles r ON r.oid = m.roleid ORDER BY r.rolname;
SELECT count(*) AS direct_membership_count FROM pg_auth_members
WHERE member = (SELECT oid FROM pg_roles WHERE rolname = current_user);
SELECT COALESCE((SELECT pg_has_role(current_user, oid, 'MEMBER')
  FROM pg_roles WHERE rolname = 'neon_superuser'), false) AS neon_superuser_member;
SHOW default_transaction_read_only;
SHOW statement_timeout;

-- ===== TRANSACTION PROBES =====
BEGIN;
-- Deliberately turn off the secondary default so failures prove ACL enforcement,
-- rather than merely proving a read-only transaction blocks all writes.
SET LOCAL transaction_read_only = off;
SET LOCAL statement_timeout = '5s';
DO $$
BEGIN
  IF current_user <> 'dashboard_reader' OR session_user <> 'dashboard_reader' THEN
    RAISE EXCEPTION 'Reconnect authenticated as dashboard_reader, not SET ROLE from owner';
  END IF;
  IF EXISTS (
    SELECT FROM pg_roles WHERE rolname = current_user
      AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls OR rolreplication)
  ) OR EXISTS (
    SELECT FROM pg_auth_members
    WHERE member = (SELECT oid FROM pg_roles WHERE rolname = current_user)
  ) THEN
    RAISE EXCEPTION 'Reader has elevated flags or memberships; verification failed';
  END IF;
END $$;

-- Must succeed and return one published snapshot; no review payload is printed.
SELECT snapshot_id, imported_at FROM dashboard.snapshots
WHERE published = true ORDER BY imported_at DESC, snapshot_id ASC LIMIT 1;
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM dashboard.snapshots WHERE published) THEN
    RAISE EXCEPTION 'No published snapshot';
  END IF;
END $$;

-- Each statement must fail with insufficient_privilege (SQLSTATE 42501).
-- If a probe unexpectedly succeeds, raise and abort; outer ROLLBACK removes it.
-- DML probes affect zero rows even if permissions are accidentally too broad.
DO $$
DECLARE probe text;
BEGIN
  FOREACH probe IN ARRAY ARRAY[
    'INSERT INTO dashboard.snapshots(snapshot_id,payload,published) SELECT snapshot_id,payload,published FROM dashboard.snapshots WHERE false',
    'UPDATE dashboard.snapshots SET published=published WHERE false',
    'DELETE FROM dashboard.snapshots WHERE false',
    format('CREATE TABLE dashboard.%I (id integer)', 'reader_probe_' || pg_backend_pid()),
    format('CREATE TABLE public.%I (id integer)', 'reader_probe_' || pg_backend_pid()),
    format('CREATE SCHEMA %I', 'reader_probe_' || pg_backend_pid()),
    format('CREATE TEMP TABLE %I (id integer)', 'reader_probe_' || pg_backend_pid())
  ] LOOP
    BEGIN
      EXECUTE probe;
      RAISE EXCEPTION 'FAILED: probe unexpectedly succeeded: %', probe;
    EXCEPTION WHEN insufficient_privilege THEN
      RAISE NOTICE 'PASS: denied (42501): %', probe;
    END;
  END LOOP;
END $$;
ROLLBACK;
