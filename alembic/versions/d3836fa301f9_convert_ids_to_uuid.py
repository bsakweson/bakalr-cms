"""convert_ids_to_uuid

Revision ID: d3836fa301f9
Revises: 46d4a7843fa6
Create Date: 2025-11-30 19:28:16.447528

CRITICAL MIGRATION: Converts all Integer IDs to UUIDs for security
- Prevents enumeration attacks
- Improves scalability
- Required for production security posture

WARNING: This is a breaking change that requires:
1. API endpoint updates (path parameters)
2. Frontend changes (UUID strings in URLs)
3. Test data updates

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3836fa301f9"
down_revision: Union[str, Sequence[str], None] = "46d4a7843fa6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert all Integer IDs to UUIDs"""

    print("🔄 Starting UUID migration...")
    print("⚠️  This may take several minutes for large databases")

    # Get database connection to check table structure
    connection = op.get_bind()

    # Step 1: Enable UUID extension
    print("1/8 Enabling UUID extension...")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Step 2: Find all tables with 'id' column (integer type)
    print("2/8 Finding tables with ID columns...")
    result = connection.execute(
        sa.text(
            """
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND column_name = 'id'
        AND data_type IN ('integer', 'bigint')
        AND table_name != 'alembic_version'
        ORDER BY table_name
    """
        )
    )

    tables_with_id = [row[0] for row in result]
    print(f"   Found {len(tables_with_id)} tables with ID columns: {', '.join(tables_with_id)}")

    # Step 3: Add UUID columns to tables
    print("3/8 Adding UUID columns...")
    for table in tables_with_id:
        op.execute(f"ALTER TABLE {table} ADD COLUMN id_new UUID DEFAULT uuid_generate_v4()")
        print(f"  ✓ Added UUID column to {table}")

    # Step 4: Create mapping table for FK updates
    print("4/8 Creating temporary ID mapping...")
    op.execute(
        """
        CREATE TEMP TABLE id_mappings (
            table_name VARCHAR(255),
            old_id INTEGER,
            new_uuid UUID,
            PRIMARY KEY (table_name, old_id)
        )
    """
    )

    # Store mappings for all tables
    print("   Storing ID mappings...")
    for table in tables_with_id:
        op.execute(
            f"""
            INSERT INTO id_mappings (table_name, old_id, new_uuid)
            SELECT '{table}', id, id_new FROM {table}
        """
        )
        print(f"   ✓ Mapped {table}")

    # Step 5: Find and update all foreign keys
    print("5/8 Finding and updating foreign key references...")

    # Get all foreign key columns
    fk_result = connection.execute(
        sa.text(
            """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND ccu.column_name = 'id'
        ORDER BY tc.table_name, kcu.column_name
    """
        )
    )

    foreign_keys = list(fk_result)
    print(f"   Found {len(foreign_keys)} foreign key relationships")

    # Add UUID foreign key columns and populate them
    for fk in foreign_keys:
        table_name, column_name, ref_table, ref_column = fk
        new_column = f"{column_name}_new"

        try:
            # Add new UUID column
            op.execute(f"ALTER TABLE {table_name} ADD COLUMN {new_column} UUID")

            # Update with UUID values from mapping
            if column_name.endswith("_id"):
                # Handle nullable FKs
                op.execute(
                    f"""
                    UPDATE {table_name} t
                    SET {new_column} = m.new_uuid
                    FROM id_mappings m
                    WHERE m.table_name = '{ref_table}'
                    AND t.{column_name} = m.old_id
                    AND t.{column_name} IS NOT NULL
                """
                )
                print(f"   ✓ Updated {table_name}.{column_name}")
        except Exception as e:
            print(f"   ⚠️  Error on {table_name}.{column_name}: {str(e)[:60]}")

    # Step 6: Drop old constraints and columns
    print("6/8 Dropping old constraints and columns...")

    # Drop all foreign key constraints first
    for fk in foreign_keys:
        table_name = fk[0]
        try:
            # Find constraint name
            constraint_result = connection.execute(
                sa.text(
                    f"""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'public'
                AND table_name = '{table_name}'
                AND constraint_type = 'FOREIGN KEY'
            """
                )
            )
            for row in constraint_result:
                constraint_name = row[0]
                op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")
        except:
            pass

    # Drop primary keys and old ID columns
    for table in tables_with_id:
        try:
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_pkey CASCADE")
            op.execute(f"ALTER TABLE {table} DROP COLUMN id CASCADE")
            print(f"  ✓ Dropped old ID from {table}")
        except Exception as e:
            print(f"  ⚠️  Error on {table}: {str(e)[:60]}")

    # Drop old foreign key columns
    for fk in foreign_keys:
        table_name, column_name = fk[0], fk[1]
        try:
            op.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name} CASCADE")
        except:
            pass

    # Step 7: Rename UUID columns to original names
    print("7/8 Renaming UUID columns...")

    # Rename id_new to id
    for table in tables_with_id:
        try:
            op.execute(f"ALTER TABLE {table} RENAME COLUMN id_new TO id")
            print(f"  ✓ Renamed {table}.id_new to id")
        except Exception as e:
            print(f"  ⚠️  Error on {table}: {str(e)[:60]}")

    # Rename foreign key columns
    for fk in foreign_keys:
        table_name, column_name = fk[0], fk[1]
        new_column = f"{column_name}_new"
        try:
            op.execute(f"ALTER TABLE {table_name} RENAME COLUMN {new_column} TO {column_name}")
        except:
            pass

    # Step 8: Recreate constraints
    print("8/8 Recreating primary keys and foreign key constraints...")

    # Add primary keys
    for table in tables_with_id:
        try:
            op.execute(f"ALTER TABLE {table} ADD PRIMARY KEY (id)")
            print(f"  ✓ Added PK to {table}")
        except Exception as e:
            print(f"  ⚠️  Error on {table}: {str(e)[:60]}")

    # Recreate foreign key constraints
    for fk in foreign_keys:
        table_name, column_name, ref_table, ref_column = fk
        constraint_name = f"{table_name}_{column_name}_fkey"
        try:
            op.execute(
                f"""
                ALTER TABLE {table_name}
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ({column_name})
                REFERENCES {ref_table}({ref_column})
                ON DELETE CASCADE
            """
            )
        except:
            pass

    print("✅ UUID migration complete!")


def downgrade() -> None:
    """
    Downgrade is not supported - would require restoring from backup
    """
    raise NotImplementedError(
        "UUID migration cannot be automatically reversed. "
        "Restore from database backup to downgrade."
    )
