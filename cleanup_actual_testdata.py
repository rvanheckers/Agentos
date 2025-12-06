#!/usr/bin/env python3
"""
Clean actual AgentOS test data based on discovered table structure
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def main():
    # Database connection from .env
    db_url = os.getenv('DATABASE_URL', 'postgresql://agentos_user:secure_agentos_2024@localhost:5432/agentos_production')

    # Parse connection string
    parts = db_url.replace('postgresql://', '').split('/')
    db_name = parts[1]
    user_pass_host = parts[0].split('@')
    host_port = user_pass_host[1].split(':')
    user_pass = user_pass_host[0].split(':')

    conn_params = {
        'host': host_port[0],
        'port': int(host_port[1]) if len(host_port) > 1 else 5432,
        'database': db_name,
        'user': user_pass[0],
        'password': user_pass[1] if len(user_pass) > 1 else ''
    }

    print(f"🔍 Connecting to AgentOS database...")

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()

        # Tables to clean (based on your actual schema)
        # Keep system_config, but clean test data
        cleanup_tables = [
            'clips',              # 12 records - test video clips
            'content_insights',   # 77 records - analysis results
            'jobs',              # 8 records - processing jobs
            'audit_logs'         # 38 records - can be cleaned for fresh start
        ]

        # Tables to KEEP (don't touch these)
        preserve_tables = [
            'clips_backup_20250728',  # Backup data
            'jobs_backup_20250728',   # Backup data
            'system_config',          # System configuration
            'processing_steps',       # Empty but keep structure
            'system_events',          # Empty but keep structure
            'system_logs',            # Empty but keep structure
            'users'                   # Empty but keep structure
        ]

        print("📊 Current data status:")
        total_to_delete = 0

        for table in cleanup_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                total_to_delete += count
                print(f"   🗑️  {table}: {count} records (WILL BE DELETED)")
            except psycopg2.Error:
                print(f"   ⚠️  {table}: table doesn't exist")

        print("\n💾 Tables to PRESERVE:")
        for table in preserve_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"   ✅ {table}: {count} records (PRESERVED)")
            except psycopg2.Error:
                print(f"   ⚠️  {table}: table doesn't exist")

        print(f"\n⚠️  This will delete {total_to_delete} total records.")
        print("💾 System config and backups will be preserved.")
        print("🆕 Database will be ready for fresh faster-whisper testing.")

        confirm = input("\nProceed with cleanup? (yes/no): ").lower().strip()

        if confirm == 'yes':
            deleted_total = 0

            # Clean in order to avoid foreign key issues
            for table in cleanup_tables:
                try:
                    cur.execute(f"DELETE FROM {table}")
                    deleted_count = cur.rowcount
                    deleted_total += deleted_count
                    print(f"   ✅ {table}: deleted {deleted_count} records")
                except psycopg2.Error as e:
                    print(f"   ❌ {table}: error - {e}")

            # Commit changes
            conn.commit()
            print(f"\n🎉 Cleanup complete! Deleted {deleted_total} total records.")

            # Reset sequences
            print("🔄 Resetting ID sequences...")
            for table in cleanup_tables:
                try:
                    cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false)")
                except psycopg2.Error:
                    pass

            conn.commit()
            print("✅ Sequences reset.")
            print("\n🚀 Database is now clean and ready for faster-whisper testing!")

        else:
            print("❌ Cleanup cancelled.")

        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()