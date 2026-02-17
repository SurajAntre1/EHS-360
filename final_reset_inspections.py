import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ehs360_project.settings')
django.setup()

from django.db import connection
import shutil

print("="*70)
print("FIXING MIGRATION CONFLICTS")
print("="*70)

# Step 1: Clear migration history
print("\n[Step 1/4] Clearing migration history...")
with connection.cursor() as cursor:
    try:
        cursor.execute("DELETE FROM django_migrations WHERE app='inspections';")
        print("  ✓ Cleared inspections migration history")
    except Exception as e:
        print(f"  ⚠ Error: {e}")

# Step 2: Delete migration files
print("\n[Step 2/4] Deleting migration files...")
migrations_dir = 'apps/inspections/migrations'

if os.path.exists(migrations_dir):
    deleted = 0
    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(migrations_dir, filename)
            try:
                os.remove(filepath)
                print(f"  ✓ Deleted: {filename}")
                deleted += 1
            except Exception as e:
                print(f"  ⚠ Error deleting {filename}: {e}")
    
    # Delete __pycache__
    pycache = os.path.join(migrations_dir, '__pycache__')
    if os.path.exists(pycache):
        try:
            shutil.rmtree(pycache)
            print(f"  ✓ Deleted __pycache__")
        except:
            pass
    
    print(f"\n  Total files deleted: {deleted}")
else:
    print(f"  ⚠ Migrations directory not found: {migrations_dir}")

print("\n" + "="*70)
print("✅ CLEANUP COMPLETE!")
print("="*70)
print("\nNow run:")
print("  1. python manage.py makemigrations inspections")
print("  2. python manage.py migrate inspections --fake")
print("  3. python manage.py runserver")