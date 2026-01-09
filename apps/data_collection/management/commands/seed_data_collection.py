# apps/data_collection/management/commands/seed_data_collection.py
"""
Django management command to seed initial data for data collection module
Run with: python manage.py seed_data_collection
"""

from django.core.management.base import BaseCommand
from apps.data_collection.models import DataCollectionCategory, DataCollectionQuestion
import json


class Command(BaseCommand):
    help = 'Seed initial categories and questions for data collection'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting data seeding...')
        
        # Create Categories based on your Excel structure
        categories_data = [
            {
                'name': 'Waste Management',
                'code': 'WASTE',
                'description': 'Waste generation, disposal and recycling data',
                'icon_class': 'fas fa-trash-alt',
                'display_order': 1,
            },
            {
                'name': 'Water Consumption',
                'code': 'WATER',
                'description': 'Water usage and consumption metrics',
                'icon_class': 'fas fa-tint',
                'display_order': 2,
            },
            {
                'name': 'Energy Consumption',
                'code': 'ENERGY',
                'description': 'Energy consumption from various sources',
                'icon_class': 'fas fa-bolt',
                'display_order': 3,
            },
            {
                'name': 'Air Emissions',
                'code': 'EMISSIONS',
                'description': 'Air emissions and atmospheric releases',
                'icon_class': 'fas fa-smog',
                'display_order': 4,
            },
            {
                'name': 'Occupational Health & Safety',
                'code': 'OHS',
                'description': 'Health and safety incidents and metrics',
                'icon_class': 'fas fa-user-shield',
                'display_order': 5,
            },
            {
                'name': 'Training & Compliance',
                'code': 'TRAINING',
                'description': 'Safety training and compliance activities',
                'icon_class': 'fas fa-graduation-cap',
                'display_order': 6,
            },
            {
                'name': 'Environmental Monitoring',
                'code': 'ENV_MONITOR',
                'description': 'Environmental monitoring and observations',
                'icon_class': 'fas fa-leaf',
                'display_order': 7,
            },
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = DataCollectionCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            categories[cat_data['code']] = category
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'{status}: {category.name}')
        
        # Create Questions based on your Excel
        questions_data = [
            # Waste Management
            {
                'category': 'WASTE',
                'question_text': 'Quantity of Asbestos Waste disposed of (past month)',
                'question_code': 'WASTE_ASBESTOS_QTY',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kg',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Enter total asbestos waste quantity in kilograms',
                'display_order': 1,
            },
            {
                'category': 'WASTE',
                'question_text': 'Unused and defective of past month (Burnt/Cancelled)',
                'question_code': 'WASTE_UNUSED_BURNT',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kg',
                'is_required': False,
                'min_value': 0,
                'display_order': 2,
            },
            {
                'category': 'WASTE',
                'question_text': 'Quantity of E-waste disposed of',
                'question_code': 'WASTE_EWASTE_QTY',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kg',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Electronic waste disposed during the month',
                'display_order': 3,
            },
            {
                'category': 'WASTE',
                'question_text': 'Effluent (Wastewater) discharge out of plant premises',
                'question_code': 'WASTE_EFFLUENT_DISCHARGE',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'liters',
                'is_required': True,
                'min_value': 0,
                'display_order': 4,
            },
            
            # Water Consumption
            {
                'category': 'WATER',
                'question_text': 'Surface water consumption',
                'question_code': 'WATER_SURFACE',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'KL',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Water consumed from surface sources (rivers, lakes)',
                'display_order': 1,
            },
            {
                'category': 'WATER',
                'question_text': 'Ground water consumption',
                'question_code': 'WATER_GROUND',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'KL',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Water consumed from bore wells and underground sources',
                'display_order': 2,
            },
            {
                'category': 'WATER',
                'question_text': 'Third party water consumption',
                'question_code': 'WATER_THIRD_PARTY',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'KL',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Water purchased from municipal or private suppliers',
                'display_order': 3,
            },
            
            # Energy Consumption
            {
                'category': 'ENERGY',
                'question_text': 'Electricity consumption',
                'question_code': 'ENERGY_ELECTRICITY',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kWh',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Total electricity consumed during the month',
                'display_order': 1,
            },
            {
                'category': 'ENERGY',
                'question_text': 'Diesel consumption',
                'question_code': 'ENERGY_DIESEL',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'liters',
                'is_required': True,
                'min_value': 0,
                'display_order': 2,
            },
            {
                'category': 'ENERGY',
                'question_text': 'Natural Gas consumption',
                'question_code': 'ENERGY_NATURAL_GAS',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'm³',
                'is_required': False,
                'min_value': 0,
                'display_order': 3,
            },
            {
                'category': 'ENERGY',
                'question_text': 'LPG consumption',
                'question_code': 'ENERGY_LPG',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kg',
                'is_required': False,
                'min_value': 0,
                'display_order': 4,
            },
            
            # Air Emissions
            {
                'category': 'EMISSIONS',
                'question_text': 'NOx emissions',
                'question_code': 'EMISSIONS_NOX',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kg',
                'is_required': False,
                'min_value': 0,
                'help_text': 'Nitrogen oxide emissions',
                'display_order': 1,
            },
            {
                'category': 'EMISSIONS',
                'question_text': 'SOx emissions',
                'question_code': 'EMISSIONS_SOX',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kg',
                'is_required': False,
                'min_value': 0,
                'help_text': 'Sulfur oxide emissions',
                'display_order': 2,
            },
            {
                'category': 'EMISSIONS',
                'question_text': 'PM (Particulate Matter)',
                'question_code': 'EMISSIONS_PM',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'kg',
                'is_required': False,
                'min_value': 0,
                'display_order': 3,
            },
            
            # Occupational Health & Safety
            {
                'category': 'OHS',
                'question_text': 'Number of First Aid Cases',
                'question_code': 'OHS_FIRST_AID',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'cases',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Total first aid incidents during the month',
                'display_order': 1,
            },
            {
                'category': 'OHS',
                'question_text': 'Number of Medical Treatment Cases (MTC)',
                'question_code': 'OHS_MTC',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'cases',
                'is_required': True,
                'min_value': 0,
                'display_order': 2,
            },
            {
                'category': 'OHS',
                'question_text': 'Number of Lost Time Injuries (LTI)',
                'question_code': 'OHS_LTI',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'cases',
                'is_required': True,
                'min_value': 0,
                'display_order': 3,
            },
            {
                'category': 'OHS',
                'question_text': 'Number of Near Miss reported',
                'question_code': 'OHS_NEAR_MISS',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'cases',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Near miss incidents reported and recorded',
                'display_order': 4,
            },
            {
                'category': 'OHS',
                'question_text': 'Fire drills conducted',
                'question_code': 'OHS_FIRE_DRILLS',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'drills',
                'is_required': False,
                'min_value': 0,
                'display_order': 5,
            },
            {
                'category': 'OHS',
                'question_text': 'Number of Safety Inspections conducted',
                'question_code': 'OHS_SAFETY_INSPECTIONS',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'inspections',
                'is_required': True,
                'min_value': 0,
                'display_order': 6,
            },
            
            # Training & Compliance
            {
                'category': 'TRAINING',
                'question_text': 'Number of employees given Safety training',
                'question_code': 'TRAINING_SAFETY_COUNT',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'employees',
                'is_required': True,
                'min_value': 0,
                'help_text': 'Total employees who received safety training this month',
                'display_order': 1,
            },
            {
                'category': 'TRAINING',
                'question_text': 'Total training hours conducted',
                'question_code': 'TRAINING_HOURS',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'hours',
                'is_required': False,
                'min_value': 0,
                'display_order': 2,
            },
            {
                'category': 'TRAINING',
                'question_text': 'Number of Safety Committee meetings',
                'question_code': 'TRAINING_COMMITTEE_MEETINGS',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'meetings',
                'is_required': False,
                'min_value': 0,
                'display_order': 3,
            },
            
            # Environmental Monitoring
            {
                'category': 'ENV_MONITOR',
                'question_text': 'Number of environmental observations reported',
                'question_code': 'ENV_OBSERVATIONS',
                'field_type': 'NUMBER',
                'unit_of_measurement': 'observations',
                'is_required': False,
                'min_value': 0,
                'display_order': 1,
            },
            {
                'category': 'ENV_MONITOR',
                'question_text': 'Were any environmental incidents reported?',
                'question_code': 'ENV_INCIDENTS_REPORTED',
                'field_type': 'CHECKBOX',
                'is_required': True,
                'help_text': 'Check if any environmental incidents occurred',
                'display_order': 2,
            },
            {
                'category': 'ENV_MONITOR',
                'question_text': 'If yes, provide details',
                'question_code': 'ENV_INCIDENTS_DETAILS',
                'field_type': 'TEXTAREA',
                'is_required': False,
                'help_text': 'Describe any environmental incidents in detail',
                'max_length': 2000,
                'display_order': 3,
            },
        ]
        
        questions_created = 0
        questions_existed = 0
        
        for q_data in questions_data:
            category_code = q_data.pop('category')
            category = categories[category_code]
            
            question, created = DataCollectionQuestion.objects.get_or_create(
                category=category,
                question_code=q_data['question_code'],
                defaults={**q_data, 'category': category}
            )
            
            if created:
                questions_created += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {question.question_text}'))
            else:
                questions_existed += 1
                self.stdout.write(f'  Already exists: {question.question_text}')
        
        self.stdout.write(self.style.SUCCESS(f'\n=== Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Categories: {len(categories_data)} total'))
        self.stdout.write(self.style.SUCCESS(f'Questions created: {questions_created}'))
        self.stdout.write(self.style.SUCCESS(f'Questions already existed: {questions_existed}'))
        self.stdout.write(self.style.SUCCESS(f'Total questions: {questions_created + questions_existed}'))
        self.stdout.write(self.style.SUCCESS('\n✅ Data seeding completed successfully!'))