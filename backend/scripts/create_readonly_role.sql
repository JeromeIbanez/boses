-- Create a read-only database role for analytics/reporting queries.
-- Run this once as a PostgreSQL superuser (e.g. postgres):
--
--   psql -U postgres -d boses -f scripts/create_readonly_role.sql
--
-- After running, applications that only need to read data (dashboards,
-- analytics tools, etc.) should connect as boses_readonly rather than boses.

-- Create the role (no login by default — grant to a login user as needed)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'boses_readonly') THEN
        CREATE ROLE boses_readonly;
    END IF;
END
$$;

-- Grant connect and usage
GRANT CONNECT ON DATABASE boses TO boses_readonly;
GRANT USAGE ON SCHEMA public TO boses_readonly;

-- Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO boses_readonly;

-- Automatically grant SELECT on any future tables created by boses
ALTER DEFAULT PRIVILEGES FOR ROLE boses IN SCHEMA public
    GRANT SELECT ON TABLES TO boses_readonly;
