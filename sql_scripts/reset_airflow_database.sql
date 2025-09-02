-- ===================================================================
-- AIRFLOW DATABASE RESET SCRIPTS
-- ===================================================================
-- 
-- This file contains two different approaches to reset the Airflow
-- metadata database on AWS RDS PostgreSQL. Choose the appropriate
-- script based on your situation.
-- ===================================================================

-- -------------------------------------------------------------------
-- SCRIPT #1: SELECTIVE TABLE CLEANUP (Airflow-Only Reset)
-- -------------------------------------------------------------------
-- 
-- WHAT IT DOES:
-- - Drops only Airflow-specific metadata tables
-- - Preserves the database schema and any non-Airflow tables
-- - Maintains database users, permissions, and other database objects
-- 
-- WHEN TO USE:
-- - After a failed or inconsistent Airflow setup
-- - To resolve issues related to stale data, especially after changing
--   the Fernet key
-- - When you need to start Airflow with a clean slate but want to
--   preserve other database objects (views, functions, non-Airflow tables)
-- - When you share the database with other applications
-- 
-- ADVANTAGES:
-- - Surgical approach - only affects Airflow
-- - Preserves database permissions and users
-- - Safer for shared database environments
-- - No need to re-grant schema permissions
-- 
-- DISADVANTAGES:
-- - Must manually list all Airflow tables (could miss new ones in future versions)
-- - Less thorough than schema reset
-- - Won't fix schema-level permission issues
-- 
-- HOW TO USE:
-- 1. Connect to your AWS RDS PostgreSQL database using pgAdmin4
-- 2. Execute this entire script
-- 3. Restart Airflow services: docker compose up -d
-- 4. The airflow-init service will recreate all tables with current schema

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

-- -------------------------------------------------------------------
-- SCRIPT #2: COMPLETE SCHEMA RESET (Nuclear Option)
-- -------------------------------------------------------------------
-- 
-- WHAT IT DOES:
-- - Completely destroys and recreates the 'public' schema
-- - Removes ALL tables, views, functions, sequences, and data
-- - Resets all permissions to defaults
-- 
-- WHEN TO USE:
-- - When you have irrecoverable database corruption
-- - After major Airflow version upgrades with migration issues
-- - When Script #1 doesn't resolve the problem
-- - When you want to guarantee a completely fresh start
-- - When the database is dedicated solely to Airflow
-- 
-- ADVANTAGES:
-- - Most thorough reset possible
-- - Guaranteed to fix any schema inconsistencies
-- - Automatically handles all database objects
-- - Future-proof (works regardless of Airflow version changes)
-- 
-- DISADVANTAGES:
-- - Destroys ALL data in the public schema (not just Airflow)
-- - Removes any custom database objects you may have created
-- - Requires re-granting permissions to your database user
-- - More disruptive than selective approach
-- 
-- HOW TO USE:
-- 1. Connect to your AWS RDS PostgreSQL database using pgAdmin4
-- 2. Execute this entire script
-- 3. If you get "role postgres does not exist" error, replace 'postgres' 
--    with your actual database username (e.g., 'joelu')
-- 4. Restart Airflow services: docker compose up -d

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Grant permissions to standard postgres user (if it exists)
-- Note: This may fail on AWS RDS where 'postgres' user doesn't exist
GRANT ALL ON SCHEMA public TO postgres;

-- Grant permissions to public (required for proper schema access)
GRANT ALL ON SCHEMA public TO public;

-- If the postgres grant failed, uncomment and modify the line below
-- with your actual database username:
-- GRANT ALL ON SCHEMA public TO joelu;

-- ===================================================================
-- SUMMARY OF DIFFERENCES:
-- ===================================================================
-- 
-- Script #1 (Selective):
-- - Surgical removal of Airflow tables only
-- - Preserves other database objects
-- - Safer for shared environments
-- - Requires manual table listing
-- 
-- Script #2 (Nuclear):
-- - Complete schema destruction and recreation
-- - Removes everything in the public schema
-- - Guarantees clean slate
-- - Requires permission re-grants
-- 
-- RECOMMENDATION:
-- - Use Script #1 first for most situations
-- - Use Script #2 only when Script #1 doesn't resolve the issue
-- - Always backup your database before running either script