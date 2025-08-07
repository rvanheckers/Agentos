#!/usr/bin/env python3
"""
PostgreSQL Database Inspector - Visual Terminal Overview
Toont tabellen, indexen, statistieken en performance data
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import sys

# Database connection
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "agentos_production",
    "user": "agentos_user",
    "password": "secure_agentos_2024"
}

def print_header(title):
    """Print a fancy header"""
    width = 80
    print("\n" + "=" * width)
    print(f"🐘 {title.center(width-4)} 🐘")
    print("=" * width)

def print_section(title):
    """Print a section header"""
    print(f"\n📊 {title}")
    print("-" * 60)

def get_database_overview():
    """Get high level database stats"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print_header("POSTGRESQL DATABASE INSPECTOR")
        print(f"🕐 Scan tijd: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Database version and size
        cursor.execute("SELECT version()")
        version = cursor.fetchone()['version']
        print(f"📦 Versie: {version.split(',')[0]}")
        
        cursor.execute("""
            SELECT pg_size_pretty(pg_database_size('agentos_production')) as size
        """)
        db_size = cursor.fetchone()['size']
        print(f"💾 Database grootte: {db_size}")
        
        # Active connections
        cursor.execute("""
            SELECT count(*) as connections 
            FROM pg_stat_activity 
            WHERE datname = 'agentos_production'
        """)
        connections = cursor.fetchone()['connections']
        print(f"🔗 Actieve connecties: {connections}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connectie gefaald: {e}")
        return False

def get_tables_overview():
    """Get all tables with row counts and sizes"""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print_section("TABELLEN OVERZICHT")
    
    cursor.execute("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_stat_get_live_tuples(c.oid) AS row_count
        FROM pg_tables pt
        JOIN pg_class c ON c.relname = pt.tablename
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
    """)
    
    tables = cursor.fetchall()
    
    print(f"{'Tabel':<20} {'Rijen':<10} {'Grootte':<10} {'Status':<15}")
    print("-" * 60)
    
    total_rows = 0
    for table in tables:
        row_count = table['row_count'] or 0
        total_rows += row_count
        status = "✅ Data" if row_count > 0 else "📭 Leeg"
        print(f"{table['tablename']:<20} {row_count:<10} {table['size']:<10} {status:<15}")
    
    print("-" * 60)
    print(f"{'TOTAAL':<20} {total_rows:<10}")
    
    conn.close()

def get_indexes_overview():
    """Get all indexes for each table"""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print_section("INDEXEN OVERZICHT")
    
    cursor.execute("""
        SELECT 
            schemaname,
            tablename,
            indexname,
            indexdef,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
        FROM pg_indexes 
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)
    
    indexes = cursor.fetchall()
    
    current_table = None
    table_index_count = {}
    
    for idx in indexes:
        table = idx['tablename']
        
        if table != current_table:
            if current_table:
                print()
            print(f"\n🗂️  {table.upper()}")
            current_table = table
            table_index_count[table] = 0
        
        table_index_count[table] += 1
        idx_type = "🔑 PRIMARY" if "pkey" in idx['indexname'] else "📇 INDEX"
        
        # Extract column info from indexdef
        if "btree" in idx['indexdef']:
            idx_type += " (B-Tree)"
        elif "unique" in idx['indexdef'].lower():
            idx_type = "🔐 UNIQUE " + idx_type
            
        print(f"   {idx_type:<20} {idx['indexname']:<30} {idx['index_size']:<10}")
    
    print_section("INDEX STATISTIEKEN")
    total_indexes = sum(table_index_count.values())
    print(f"📊 Totaal aantal indexen: {total_indexes}")
    
    for table, count in table_index_count.items():
        print(f"   {table:<20} {count} indexen")
    
    conn.close()

def get_performance_stats():
    """Get performance statistics"""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print_section("PERFORMANCE STATISTIEKEN")
    
    # Table activity
    cursor.execute("""
        SELECT 
            schemaname,
            relname as table_name,
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes
        FROM pg_stat_user_tables
        ORDER BY (seq_scan + idx_scan) DESC
    """)
    
    stats = cursor.fetchall()
    
    print("🚀 TABEL ACTIVITEIT:")
    print(f"{'Tabel':<20} {'Seq Scans':<10} {'Index Scans':<12} {'Inserts':<8} {'Updates':<8} {'Deletes':<8}")
    print("-" * 75)
    
    for stat in stats:
        seq_scans = stat['seq_scan'] or 0
        idx_scans = stat['idx_scan'] or 0
        inserts = stat['inserts'] or 0
        updates = stat['updates'] or 0
        deletes = stat['deletes'] or 0
        
        print(f"{stat['table_name']:<20} {seq_scans:<10} {idx_scans:<12} {inserts:<8} {updates:<8} {deletes:<8}")
    
    # Index usage
    print("\n🎯 INDEX USAGE:")
    cursor.execute("""
        SELECT 
            schemaname,
            relname as tablename,
            indexrelname as indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        WHERE idx_scan > 0
        ORDER BY idx_scan DESC
        LIMIT 10
    """)
    
    idx_stats = cursor.fetchall()
    
    if idx_stats:
        print(f"{'Index':<30} {'Scans':<10} {'Tuples Read':<12} {'Tuples Fetched':<15}")
        print("-" * 70)
        for idx in idx_stats:
            print(f"{idx['indexname']:<30} {idx['idx_scan']:<10} {idx['idx_tup_read']:<12} {idx['idx_tup_fetch']:<15}")
    else:
        print("📭 Nog geen index usage statistieken (database is nieuw)")
    
    conn.close()

def get_connection_info():
    """Get current connection information"""
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print_section("VERBINDING INFORMATIE")
    
    cursor.execute("""
        SELECT 
            datname as database,
            usename as username,
            application_name,
            client_addr,
            state,
            query_start,
            state_change
        FROM pg_stat_activity 
        WHERE datname = 'agentos_production'
        AND pid != pg_backend_pid()
    """)
    
    connections = cursor.fetchall()
    
    if connections:
        print(f"{'App':<20} {'User':<15} {'State':<10} {'Client':<15}")
        print("-" * 65)
        for conn_info in connections:
            app_name = conn_info['application_name'] or 'Unknown'
            client = conn_info['client_addr'] or 'local'
            print(f"{app_name:<20} {conn_info['username']:<15} {conn_info['state']:<10} {str(client):<15}")
    else:
        print("📭 Geen andere actieve verbindingen")
    
    conn.close()

def main():
    """Main inspector function"""
    if not get_database_overview():
        sys.exit(1)
    
    get_tables_overview()
    get_indexes_overview()
    get_performance_stats()
    get_connection_info()
    
    print_header("INSPECTIE VOLTOOID")
    print("💡 Tips:")
    print("   - Gebruik 'python database/postgresql_inspector.py' voor updates")
    print("   - Check Grafana op http://172.30.108.252:3000 voor real-time monitoring")
    print("   - Admin UI op http://localhost:8004 voor service stats")

if __name__ == "__main__":
    main()