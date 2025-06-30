#!/usr/bin/env python3
"""Check database for columns with all NULL values."""

import sqlite3
import sys
from pathlib import Path

def check_null_columns(db_path: str):
    """Check which columns have all NULL values in each table."""
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        
        print(f"🔍 Checking NULL columns in database: {db_path}")
        print("=" * 80)
        
        total_null_columns = 0
        
        for table_name, in tables:
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            total_rows = cursor.fetchone()[0]
            
            if total_rows == 0:
                print(f"\n📊 Table: {table_name} (0 rows - skipping)")
                continue
            
            null_columns = []
            
            for col in columns_info:
                col_name = col[1]  # Column name is at index 1
                
                # Count non-NULL values
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NOT NULL;")
                non_null_count = cursor.fetchone()[0]
                
                if non_null_count == 0:
                    null_columns.append(col_name)
            
            # Report results for this table
            print(f"\n📊 Table: {table_name} ({total_rows} rows)")
            
            if null_columns:
                print(f"❌ Columns with ALL NULL values ({len(null_columns)} columns):")
                for col in null_columns:
                    print(f"  • {col}")
                total_null_columns += len(null_columns)
            else:
                print("✅ No columns with all NULL values")
        
        print("\n" + "=" * 80)
        print(f"📈 SUMMARY: Found {total_null_columns} columns with all NULL values across all tables")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_specific_columns(db_path: str, table_name: str, columns: list):
    """Check specific columns for NULL values."""
    
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        total_rows = cursor.fetchone()[0]
        
        print(f"\n🔍 Checking specific columns in {table_name} ({total_rows} rows):")
        print("-" * 50)
        
        for col in columns:
            try:
                # Count non-NULL values
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NOT NULL;")
                non_null_count = cursor.fetchone()[0]
                
                null_count = total_rows - non_null_count
                percentage = (null_count / total_rows * 100) if total_rows > 0 else 0
                
                status = "❌" if non_null_count == 0 else "✅" if null_count == 0 else "⚠️ "
                print(f"{status} {col}: {non_null_count} non-NULL, {null_count} NULL ({percentage:.1f}%)")
                
            except sqlite3.Error as e:
                print(f"❌ {col}: Error - {e}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Default database path
    db_path = "health.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # Check all columns for NULL values
    check_null_columns(db_path)
    
    # Check specific sleep and health columns
    sleep_columns = [
        'sleep_duration_hours', 'deep_sleep_hours', 'light_sleep_hours', 
        'rem_sleep_hours', 'awake_hours', 'deep_sleep_percentage', 
        'light_sleep_percentage', 'rem_sleep_percentage', 'awake_percentage'
    ]
    
    health_columns = [
        'step_goal', 'resting_heart_rate', 'max_heart_rate', 'min_heart_rate',
        'average_heart_rate', 'avg_stress_level', 'average_spo2', 'average_respiration'
    ]
    
    check_specific_columns(db_path, 'daily_health_metrics', sleep_columns + health_columns)