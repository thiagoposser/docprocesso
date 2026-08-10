-- Runs only when PostgreSQL initializes a new data volume.
-- Extensions shared by most modern applications can be declared here.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
COMMENT ON EXTENSION "uuid-ossp" IS 'UUID generation helpers enabled by the base template';
