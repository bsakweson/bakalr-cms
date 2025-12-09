#!/bin/bash
# Initialize multiple PostgreSQL databases
# Used by docker-compose to create both bakalr_cms and boutique databases

set -e
set -u

function create_user_and_database() {
    local database=$1
    local user=$2
    local password=$3

    echo "Creating user '$user' and database '$database'..."

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        -- Create user if not exists
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$user') THEN
                CREATE USER $user WITH PASSWORD '$password';
            END IF;
        END
        \$\$;

        -- Create database if not exists
        SELECT 'CREATE DATABASE $database OWNER $user'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec

        -- Grant privileges
        GRANT ALL PRIVILEGES ON DATABASE $database TO $user;
EOSQL

    echo "User '$user' and database '$database' created successfully."
}

# Main execution
echo "=== PostgreSQL Multi-Database Initialization ==="

# Create bakalr_cms database (for CMS)
create_user_and_database \
    "${CMS_DB_NAME:-bakalr_cms}" \
    "${CMS_DB_USER:-bakalr}" \
    "${CMS_DB_PASSWORD:-bakalr_password}"

# Create boutique database (for microservices)
create_user_and_database \
    "${BOUTIQUE_DB_NAME:-boutique}" \
    "${BOUTIQUE_DB_USER:-boutique}" \
    "${BOUTIQUE_DB_PASSWORD:-boutique_password}"

# Initialize boutique schema
echo "Initializing boutique database schema..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "boutique" <<-EOSQL
    -- Create schemas for different domains
    CREATE SCHEMA IF NOT EXISTS inventory;
    CREATE SCHEMA IF NOT EXISTS orders;
    CREATE SCHEMA IF NOT EXISTS payments;
    CREATE SCHEMA IF NOT EXISTS shipping;
    CREATE SCHEMA IF NOT EXISTS audit;
    CREATE SCHEMA IF NOT EXISTS notifications;

    -- Grant schema access to boutique user
    GRANT ALL ON SCHEMA inventory TO boutique;
    GRANT ALL ON SCHEMA orders TO boutique;
    GRANT ALL ON SCHEMA payments TO boutique;
    GRANT ALL ON SCHEMA shipping TO boutique;
    GRANT ALL ON SCHEMA audit TO boutique;
    GRANT ALL ON SCHEMA notifications TO boutique;

    -- Set search path for boutique user
    ALTER USER boutique SET search_path TO public, inventory, orders, payments, shipping, audit, notifications;
EOSQL

echo "=== Database initialization complete ==="
