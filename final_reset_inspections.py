import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ehs360_project.settings')  # ✅ FIXED
django.setup()

from django.db import connection
from django.core.management import call_command
import shutil

print("="*70)
print("FINAL COMPLETE RESET OF INSPECTIONS APP")
print("="*70)

# Step 1: Drop ALL inspection tables
print("\n[Step 1/5] Dropping ALL inspection tables...")
with connection.cursor() as cursor:
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'inspection%';")
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} inspection tables to drop:")
    for (table_name,) in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            print(f"  ✓ Dropped: {table_name}")
        except Exception as e:
            print(f"  ⚠ Error dropping {table_name}: {e}")
    
    # Also drop template question mapping table
    try:
        cursor.execute("DROP TABLE IF EXISTS template_questions;")
        print(f"  ✓ Dropped: template_questions")
    except:
        pass
    
    # Clear migration history
    cursor.execute("DELETE FROM django_migrations WHERE app='inspections';")
    print("\n  ✓ Cleared migration history")
    
    cursor.execute("PRAGMA foreign_keys = ON;")

# Step 2: Delete migration files
print("\n[Step 2/5] Deleting migration files...")
migrations_dir = 'apps/inspections/migrations'

if os.path.exists(migrations_dir):
    deleted_count = 0
    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(migrations_dir, filename)
            try:
                os.remove(filepath)
                print(f"  ✓ Deleted: {filename}")
                deleted_count += 1
            except Exception as e:
                print(f"  ⚠ Error deleting {filename}: {e}")
    
    # Delete __pycache__
    pycache_dir = os.path.join(migrations_dir, '__pycache__')
    if os.path.exists(pycache_dir):
        try:
            shutil.rmtree(pycache_dir)
            print(f"  ✓ Deleted: __pycache__")
        except:
            pass
    
    print(f"\n  Total migration files deleted: {deleted_count}")

# Step 3: Verify tables are gone
print("\n[Step 3/5] Verifying tables are dropped...")
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'inspection%';")
    remaining = cursor.fetchall()
    
    if remaining:
        print(f"  ⚠ WARNING: {len(remaining)} inspection tables still exist:")
        for (table_name,) in remaining:
            print(f"    - {table_name}")
    else:
        print("  ✅ All inspection tables successfully dropped")

# Step 4: Create fresh migrations
print("\n[Step 4/5] Creating fresh migrations...")
try:
    call_command('makemigrations', 'inspections', verbosity=2)
    print("  ✅ Migrations created successfully")
except Exception as e:
    print(f"  ❌ Error creating migrations: {e}")
    exit(1)

# Step 5: Apply migrations
print("\n[Step 5/5] Applying migrations...")
try:
    call_command('migrate', 'inspections', verbosity=2)
    print("  ✅ Migrations applied successfully")
except Exception as e:
    print(f"  ❌ Error applying migrations: {e}")
    exit(1)

# Verification
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

with connection.cursor() as cursor:
    # Check if InspectionResponse table exists with correct columns
    cursor.execute("PRAGMA table_info(inspections_inspectionresponse);")
    columns = cursor.fetchall()
    
    if columns:
        print(f"\n✅ inspections_inspectionresponse table created with {len(columns)} columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Check for required columns
        column_names = [col[1] for col in columns]
        required_columns = [
            'id', 'submission_id', 'question_id', 'answer', 'remarks', 
            'photo', 'answered_at', 'assigned_to_id', 'assigned_by_id', 
            'assigned_at', 'assignment_remarks', 'converted_to_hazard_id'
        ]
        
        missing = [col for col in required_columns if col not in column_names]
        if missing:
            print(f"\n  ⚠ Missing columns: {missing}")
        else:
            print(f"\n  ✅ All required columns present!")
    else:
        print("\n  ❌ inspections_inspectionresponse table not found!")

print("\n" + "="*70)
print("✅ RESET COMPLETE!")
print("="*70)
print("\nYou can now run: python manage.py runserver")