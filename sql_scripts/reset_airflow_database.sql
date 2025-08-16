-- =============================================================================
-- WARNING: DESTRUCTIVE SCRIPT. EXECUTE WITH CAUTION.
-- =============================================================================
--
-- Purpose:
-- This script completely resets the Apache Airflow environment by dropping all
-- of its metadata tables from the database.
--
-- When to Use:
-- - After a failed or inconsistent initial setup.
-- - To resolve issues related to stale data, especially after changing
--   the Fernet key.
-- - When you need to start Airflow with a completely clean slate without
--   deleting the entire database/schema.
--
-- How to Use:
-- 1. Connect to the PostgreSQL database that Airflow uses.
-- 2. Execute this entire script.
-- 3. Restart the Airflow services (docker compose up). The `airflow-init`
--    service will now run on a clean database and re-create all tables.
--
-- Last Verified: Airflow 2.8.x
--
-- =============================================================================

DROP TABLE IF EXISTS "job" CASCADE;
DROP TABLE IF EXISTS "slot_pool" CASCADE;
DROP TABLE IF EXISTS "log" CASCADE;
DROP TABLE IF EXISTS "dag_code" CASCADE;
DROP TABLE IF EXISTS "dag_pickle" CASCADE;
DROP TABLE IF EXISTS "ab_user" CASCADE;
DROP TABLE IF EXISTS "ab_register_user" CASCADE;
DROP TABLE IF EXISTS "connection" CASCADE;
DROP TABLE IF EXISTS "variable" CASCADE;
DROP TABLE IF EXISTS "dag_schedule_dataset_reference" CASCADE;
DROP TABLE IF EXISTS "task_outlet_dataset_reference" CASCADE;
DROP TABLE IF EXISTS "dag_run" CASCADE;
DROP TABLE IF EXISTS "dag_tag" CASCADE;
DROP TABLE IF EXISTS "dag_owner_attributes" CASCADE;
DROP TABLE IF EXISTS "ab_permission" CASCADE;
DROP TABLE IF EXISTS "ab_permission_view" CASCADE;
DROP TABLE IF EXISTS "ab_view_menu" CASCADE;
DROP TABLE IF EXISTS "ab_user_role" CASCADE;
DROP TABLE IF EXISTS "ab_role" CASCADE;
DROP TABLE IF EXISTS "dag_warning" CASCADE;
DROP TABLE IF EXISTS "dagrun_dataset_event" CASCADE;
DROP TABLE IF EXISTS "task_instance" CASCADE;
DROP TABLE IF EXISTS "dag_run_note" CASCADE;
DROP TABLE IF EXISTS "ab_permission_view_role" CASCADE;
DROP TABLE IF EXISTS "task_fail" CASCADE;
DROP TABLE IF EXISTS "task_map" CASCADE;
DROP TABLE IF EXISTS "task_reschedule" CASCADE;
DROP TABLE IF EXISTS "xcom" CASCADE;
DROP TABLE IF EXISTS "task_instance_note" CASCADE;
DROP TABLE IF EXISTS "session" CASCADE;
DROP TABLE IF EXISTS "alembic_version" CASCADE;