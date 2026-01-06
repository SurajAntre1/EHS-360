
from django.core.management.base import BaseCommand
from apps.inspections.models import InspectionTemplate, InspectionCategory, InspectionPoint
import csv


class Command(BaseCommand):
    help = 'Import Fire Safety Inspection Checklist from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file'
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        self.stdout.write(self.style.SUCCESS('Starting import...'))
        
        # Create or get template
        template, created = InspectionTemplate.objects.get_or_create(
            template_code='FSIC',
            defaults={
                'template_name': 'Fire Safety Inspection Checklist',
                'description': 'Monthly fire safety inspection for all locations',
                'frequency': 'MONTHLY',
                'document_number': 'EIL/FSIC/EHS/F-01',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created template: {template.template_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Template already exists: {template.template_name}'))
        
        # Read CSV file
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                # Skip first 3 header rows
                for _ in range(3):
                    next(file)
                
                reader = csv.reader(file)
                
                current_category = None
                category_sequence = 0
                point_sequence = 0
                
                for row in reader:
                    # Skip empty rows
                    if not any(row):
                        continue
                    
                    # Skip footer rows
                    if row[0] in ['Checked By', 'Reviewed By', 'Month', 'Signature', 'Prepared BY', '']:
                        continue
                    
                    area = row[0].strip() if row[0] else ''
                    inspection_point = row[1].strip() if len(row) > 1 and row[1] else ''
                    
                    # If area column has value, it's a new category
                    if area and inspection_point:
                        category_sequence += 1
                        point_sequence = 0
                        
                        # Create category
                        current_category, cat_created = InspectionCategory.objects.get_or_create(
                            template=template,
                            category_name=area,
                            defaults={
                                'sequence_order': category_sequence,
                                'is_active': True
                            }
                        )
                        
                        if cat_created:
                            self.stdout.write(self.style.SUCCESS(f'  ✓ Created category: {area}'))
                        
                        # Create first inspection point for this category
                        point_sequence += 1
                        InspectionPoint.objects.get_or_create(
                            category=current_category,
                            inspection_point_text=inspection_point,
                            defaults={
                                'sequence_order': point_sequence,
                                'is_mandatory': True,
                                'requires_photo': False,
                                'is_active': True
                            }
                        )
                        
                    # If only inspection_point has value, add to current category
                    elif not area and inspection_point and current_category:
                        point_sequence += 1
                        InspectionPoint.objects.get_or_create(
                            category=current_category,
                            inspection_point_text=inspection_point,
                            defaults={
                                'sequence_order': point_sequence,
                                'is_mandatory': True,
                                'requires_photo': False,
                                'is_active': True
                            }
                        )
                
                # Final statistics
                total_categories = InspectionCategory.objects.filter(template=template).count()
                total_points = InspectionPoint.objects.filter(category__template=template).count()
                
                self.stdout.write(self.style.SUCCESS('\n' + '='*50))
                self.stdout.write(self.style.SUCCESS('Import completed successfully!'))
                self.stdout.write(self.style.SUCCESS(f'Total Categories: {total_categories}'))
                self.stdout.write(self.style.SUCCESS(f'Total Inspection Points: {total_points}'))
                self.stdout.write(self.style.SUCCESS('='*50))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Error: File not found - {csv_file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during import: {str(e)}'))