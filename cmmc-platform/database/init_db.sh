#!/bin/bash
#
# Database Initialization Script
#
# This script initializes the CMMC Platform database:
# 1. Creates database and user
# 2. Enables extensions
# 3. Runs migrations
# 4. Loads seed data
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="${DB_NAME:-cmmc_db}"
DB_USER="${DB_USER:-cmmc_user}"
DB_PASSWORD="${DB_PASSWORD:-cmmc_password}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CMMC Platform - Database Initialization${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if PostgreSQL is running
print_status "Checking PostgreSQL connection..."
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    print_error "PostgreSQL is not running on $DB_HOST:$DB_PORT"
    print_error "Please start PostgreSQL and try again"
    exit 1
fi
print_status "PostgreSQL is running ✓"

# Create database and user
print_status "Creating database and user..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
EOF

print_status "Database created ✓"

# Enable extensions
print_status "Enabling PostgreSQL extensions..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
EOF

print_status "Extensions enabled ✓"

# Run Alembic migrations
print_status "Running database migrations..."
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

if [ -f "alembic.ini" ]; then
    alembic upgrade head
    print_status "Migrations applied ✓"
else
    print_warning "alembic.ini not found, skipping migrations"
    print_warning "You can manually run: alembic upgrade head"
fi

# Load seed data
print_status "Loading seed data..."
if [ -d "seeds" ]; then
    for seed_file in seeds/*.sql; do
        if [ -f "$seed_file" ]; then
            print_status "Loading $(basename $seed_file)..."
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$seed_file"
        fi
    done
    print_status "Seed data loaded ✓"
else
    print_warning "seeds directory not found, skipping seed data"
fi

# Verify installation
print_status "Verifying database installation..."
TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
print_status "Tables created: $TABLE_COUNT"

CONTROL_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM cmmc_controls" 2>/dev/null || echo "0")
print_status "CMMC controls loaded: $CONTROL_COUNT"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Database initialization complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Database: ${GREEN}$DB_NAME${NC}"
echo -e "User: ${GREEN}$DB_USER${NC}"
echo -e "Host: ${GREEN}$DB_HOST:$DB_PORT${NC}"
echo ""
echo -e "Connection string:"
echo -e "  ${YELLOW}postgresql://$DB_USER:****@$DB_HOST:$DB_PORT/$DB_NAME${NC}"
echo ""
print_status "You can now start the application!"
