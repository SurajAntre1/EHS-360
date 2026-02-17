import os
import shutil
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'everest.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def reset_inspections_complete():
    """Complete reset of inspections app - tables, migrations, everything"""
    
    print("="*60)
    print("COMPLETE RESET OF INSPECTIONS APP")
    print("="*60)
    
    # Step 1: Drop all tables
    print("\n[Step 1/4] Dropping all inspection tables...")
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        tables = [
            'inspections_inspectionresponse',
            'inspections_inspectionfinding',
            'inspections_inspectionsubmission',
            'inspections_inspectionschedule',
            'inspections_templatequestion',
            'inspections_inspectiontemplate_applicable_plants',
            'inspections_inspectiontemplate_applicable_departments',
            'inspections_inspectiontemplate',
            'inspections_inspectionquestion',
            'inspections_inspectioncategory',
        ]
        
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table};")
                print(f"  ✓ Dropped: {table}")
            except Exception as e:
                print(f"  ⚠ {table}: {e}")
        
        # Clear migration history
        cursor.execute("DELETE FROM django_migrations WHERE app='inspections';")
        print("  ✓ Cleared migration history")
        
        cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Step 2: Delete migration files
    print("\n[Step 2/4] Deleting migration files...")
    migrations_dir = 'apps/inspections/migrations'
    
    if os.path.exists(migrations_dir):
        for filename in os.listdir(migrations_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                filepath = os.path.join(migrations_dir, filename)
                try:
                    os.remove(filepath)
                    print(f"  ✓ Deleted: {filename}")
                except Exception as e:
                    print(f"  ⚠ {filename}: {e}")
            elif filename.endswith('.pyc'):
                filepath = os.path.join(migrations_dir, filename)
                try:
                    os.remove(filepath)
                except:
                    pass
        
        # Also delete __pycache__ if exists
        pycache_dir = os.path.join(migrations_dir, '__pycache__')
        if os.path.exists(pycache_dir):
            try:
                shutil.rmtree(pycache_dir)
                print("  ✓ Deleted __pycache__")
            except:
                pass
    
    # Step 3: Create fresh migrations
    print("\n[Step 3/4] Creating fresh migrations...")
    try:
        call_command('makemigrations', 'inspections', verbosity=2)
        print("  ✓ Migrations created successfully")
    except Exception as e:
        print(f"  ✗ Error creating migrations: {e}")
        return False
    
    # Step 4: Apply migrations
    print("\n[Step 4/4] Applying migrations...")
    try:
        call_command('migrate', 'inspections', verbosity=2)
        print("  ✓ Migrations applied successfully")
    except Exception as e:
        print(f"  ✗ Error applying migrations: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ RESET COMPLETE!")
    print("="*60)
    print("\nInspections app is now ready to use.")
    print("You can run: python manage.py runserver")
    
    return True

if __name__ == '__main__':
    print("\n⚠️  WARNING: This will DELETE all inspection data!")
    print("This includes:")
    print("  - All categories")
    print("  - All questions")
    print("  - All templates")
    print("  - All schedules")
    print("  - All submissions")
    print("  - All responses")
    print("  - All findings")
    
    confirm = input("\nType 'RESET' to continue: ")
    
    if confirm == 'RESET':
        reset_inspections_complete()
    else:
        print("\n❌ Reset cancelled.")