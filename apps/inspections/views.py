# apps/inspections/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

from .models import *
from .forms import *
from apps.notifications.services import NotificationService

# ====================================
# DASHBOARD
# ====================================

@login_required
def inspection_dashboard(request):
    """Main inspection dashboard"""
    
    context = {
        'total_categories': InspectionCategory.objects.filter(is_active=True).count(),
        'total_questions': InspectionQuestion.objects.filter(is_active=True).count(),
        'total_templates': InspectionTemplate.objects.filter(is_active=True).count(),
        'total_schedules': InspectionSchedule.objects.count(),
        
        # Recent data
        'recent_categories': InspectionCategory.objects.filter(is_active=True)[:5],
        'recent_questions': InspectionQuestion.objects.filter(is_active=True)[:10],
        'recent_schedules': InspectionSchedule.objects.select_related(
            'template', 'assigned_to', 'plant'
        )[:10],
    }
    
    # User-specific data
    if request.user.can_access_inspection_module or request.user.is_superuser:
        if request.user.has_permission('VIEW_INSPECTION'):
            # HOD sees their assigned inspections
            context['my_pending_inspections'] = InspectionSchedule.objects.filter(
                assigned_to=request.user,
                status__in=['SCHEDULED', 'IN_PROGRESS']
            ).count()
            context['my_overdue_inspections'] = InspectionSchedule.objects.filter(
                assigned_to=request.user,
                status='OVERDUE'
            ).count()
        
        elif request.user.can_access_inspection_module or request.user.is_superuser or request.user.is_admin:
            # Safety manager sees all for their plant
            context['pending_schedules'] = InspectionSchedule.objects.filter(
                status__in=['SCHEDULED', 'IN_PROGRESS']
            ).count()
            context['overdue_schedules'] = InspectionSchedule.objects.filter(
                status='OVERDUE'
            ).count()
    
    return render(request, 'inspections/dashboard.html', context)


# ====================================
# CATEGORY VIEWS
# ====================================

@login_required
def category_list(request):
    """List all inspection categories"""
    
    categories = InspectionCategory.objects.annotate(
        questions_count=Count('questions', filter=Q(questions__is_active=True))
    ).order_by('display_order', 'category_name')
    
    # Filter
    search = request.GET.get('search')
    if search:
        categories = categories.filter(
            Q(category_name__icontains=search) |
            Q(category_code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search
    }
    return render(request, 'inspections/category_list.html', context)


@login_required
def category_create(request):
    """Create new inspection category"""
    
    if request.method == 'POST':
        form = InspectionCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, f'Category "{category.category_name}" created successfully!')
            return redirect('inspections:category_list')
    else:
        form = InspectionCategoryForm()
    
    context = {
        'form': form,
        'action': 'Create',
        'title': 'Create New Category'
    }
    return render(request, 'inspections/category_form.html', context)


@login_required
def category_edit(request, pk):
    """Edit existing category"""
    
    category = get_object_or_404(InspectionCategory, pk=pk)
    
    if request.method == 'POST':
        form = InspectionCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.category_name}" updated successfully!')
            return redirect('inspections:category_list')
    else:
        form = InspectionCategoryForm(instance=category)
    
    context = {
        'form': form,
        'action': 'Edit',
        'title': f'Edit Category: {category.category_name}',
        'category': category
    }
    return render(request, 'inspections/category_form.html', context)


@login_required
def category_delete(request, pk):
    """Soft delete category"""
    
    category = get_object_or_404(InspectionCategory, pk=pk)
    
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Category "{category.category_name}" deleted successfully!')
        return redirect('inspections:category_list')
    
    context = {
        'category': category,
        'questions_count': category.questions.filter(is_active=True).count()
    }
    return render(request, 'inspections/category_confirm_delete.html', context)


# ====================================
# QUESTION VIEWS
# ====================================

@login_required
def question_list(request):
    """List all inspection questions with filters"""
    
    questions = InspectionQuestion.objects.select_related('category').filter(is_active=True)
    
    # Apply filters
    filter_form = QuestionFilterForm(request.GET)
    
    if filter_form.is_valid():
        category = filter_form.cleaned_data.get('category')
        question_type = filter_form.cleaned_data.get('question_type')
        is_critical = filter_form.cleaned_data.get('is_critical')
        search = filter_form.cleaned_data.get('search')
        
        if category:
            questions = questions.filter(category=category)
        
        if question_type:
            questions = questions.filter(question_type=question_type)
        
        if is_critical is not None:
            questions = questions.filter(is_critical=is_critical)
        
        if search:
            questions = questions.filter(
                Q(question_text__icontains=search) |
                Q(question_code__icontains=search) |
                Q(reference_standard__icontains=search)
            )
    
    questions = questions.order_by('category', 'display_order')
    
    # Pagination
    paginator = Paginator(questions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_questions': questions.count()
    }
    return render(request, 'inspections/question_list.html', context)


@login_required
def question_create(request):
    """Create new inspection question"""
    
    if request.method == 'POST':
        form = InspectionQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.save()
            messages.success(request, f'Question "{question.question_code}" created successfully!')
            
            # Redirect based on action
            if 'save_and_add' in request.POST:
                return redirect('inspections:question_create')
            return redirect('inspections:question_list')
    else:
        form = InspectionQuestionForm()
        
        # Pre-select category if provided
        category_id = request.GET.get('category')
        if category_id:
            form.initial['category'] = category_id
    
    context = {
        'form': form,
        'action': 'Create',
        'title': 'Create New Question'
    }
    return render(request, 'inspections/question_form.html', context)


@login_required
def question_edit(request, pk):
    """Edit existing question"""
    
    question = get_object_or_404(InspectionQuestion, pk=pk)
    
    if request.method == 'POST':
        form = InspectionQuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save(commit=False)
            question.updated_by = request.user
            question.save()
            messages.success(request, f'Question "{question.question_code}" updated successfully!')
            return redirect('inspections:question_list')
    else:
        form = InspectionQuestionForm(instance=question)
    
    context = {
        'form': form,
        'action': 'Edit',
        'title': f'Edit Question: {question.question_code}',
        'question': question
    }
    return render(request, 'inspections/question_form.html', context)


@login_required
def question_detail(request, pk):
    """View question details"""
    
    question = get_object_or_404(
        InspectionQuestion.objects.select_related('category', 'created_by'),
        pk=pk
    )
    
    # Get templates using this question
    templates = InspectionTemplate.objects.filter(
        template_questions__question=question,
        is_active=True
    ).distinct()
    
    context = {
        'question': question,
        'templates': templates
    }
    return render(request, 'inspections/question_detail.html', context)


@login_required
def question_delete(request, pk):
    """Soft delete question"""
    
    question = get_object_or_404(InspectionQuestion, pk=pk)
    
    if request.method == 'POST':
        question.is_active = False
        question.save()
        messages.success(request, f'Question "{question.question_code}" deleted successfully!')
        return redirect('inspections:question_list')
    
    context = {
        'question': question,
        'templates_count': InspectionTemplate.objects.filter(
            template_questions__question=question
        ).distinct().count()
    }
    return render(request, 'inspections/question_confirm_delete.html', context)


# apps/inspections/views.py (continued)

# ====================================
# TEMPLATE VIEWS
# ====================================

@login_required
def template_list(request):
    """List all inspection templates"""
    
    templates = InspectionTemplate.objects.annotate(
        questions_count=Count('template_questions', filter=Q(template_questions__question__is_active=True))
    ).prefetch_related('applicable_plants', 'applicable_departments')
    
    # Filters
    inspection_type = request.GET.get('inspection_type')
    plant_id = request.GET.get('plant')
    search = request.GET.get('search')
    
    if inspection_type:
        templates = templates.filter(inspection_type=inspection_type)
    
    if plant_id:
        templates = templates.filter(
            Q(applicable_plants__id=plant_id) | Q(applicable_plants__isnull=True)
        )
    
    if search:
        templates = templates.filter(
            Q(template_name__icontains=search) |
            Q(template_code__icontains=search) |
            Q(description__icontains=search)
        )
    
    templates = templates.distinct().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(templates, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # For filters
    from apps.organizations.models import Plant
    plants = Plant.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'inspection_types': InspectionTemplate.INSPECTION_TYPE_CHOICES,
        'plants': plants,
        'selected_type': inspection_type,
        'selected_plant': plant_id,
        'search': search
    }
    return render(request, 'inspections/template_list.html', context)


@login_required
def template_create(request):
    """Create new inspection template"""
    
    if request.method == 'POST':
        form = InspectionTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'Template "{template.template_name}" created successfully!')
            return redirect('inspections:template_detail', pk=template.pk)
    else:
        form = InspectionTemplateForm()
    
    context = {
        'form': form,
        'action': 'Create',
        'title': 'Create New Inspection Template'
    }
    return render(request, 'inspections/template_form.html', context)


@login_required
def template_edit(request, pk):
    """Edit existing template"""
    
    template = get_object_or_404(InspectionTemplate, pk=pk)
    
    if request.method == 'POST':
        form = InspectionTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f'Template "{template.template_name}" updated successfully!')
            return redirect('inspections:template_detail', pk=template.pk)
    else:
        form = InspectionTemplateForm(instance=template)
    
    context = {
        'form': form,
        'action': 'Edit',
        'title': f'Edit Template: {template.template_name}',
        'template': template
    }
    return render(request, 'inspections/template_form.html', context)

from collections import defaultdict

# apps/inspections/views.py

@login_required
def template_detail(request, pk):
    """View template details with all questions"""
    from collections import defaultdict
    
    template = get_object_or_404(InspectionTemplate, pk=pk)
    
    # Get all template questions with related data
    template_questions = TemplateQuestion.objects.filter(
        template=template
    ).select_related(
        'question',
        'question__category'
    ).order_by('display_order')
    
    # Group questions by category
    questions_by_category = defaultdict(list)
    for tq in template_questions:
        questions_by_category[tq.question.category].append(tq)
    
    # Convert to regular dict and sort by category display_order
    questions_by_category = dict(sorted(
        questions_by_category.items(),
        key=lambda x: x[0].display_order
    ))
    
    # Get unique categories - FIXED VERSION
    # Extract category IDs from template questions
    category_ids = template_questions.values_list(
        'question__category_id', 
        flat=True
    ).distinct()
    
    # Get categories by IDs
    categories = InspectionCategory.objects.filter(
        id__in=category_ids
    ).order_by('display_order')
    
    # Count total questions
    total_questions = template_questions.count()
    
    context = {
        'template': template,
        'questions_by_category': questions_by_category,
        'categories': categories,
        'total_questions': total_questions,
    }
    return render(request, 'inspections/template_detail.html', context)

@login_required
def template_delete(request, pk):
    """Soft delete template"""
    
    template = get_object_or_404(InspectionTemplate, pk=pk)
    
    if request.method == 'POST':
        template.is_active = False
        template.save()
        messages.success(request, f'Template "{template.template_name}" deleted successfully!')
        return redirect('inspections:template_list')
    
    context = {
        'template': template,
        'questions_count': template.get_total_questions(),
        'schedules_count': template.schedules.count()
    }
    return render(request, 'inspections/template_confirm_delete.html', context)


@login_required
def template_add_question(request, pk):
    """Add single question to template"""
    
    template = get_object_or_404(InspectionTemplate, pk=pk)
    
    if request.method == 'POST':
        form = TemplateQuestionForm(request.POST)
        if form.is_valid():
            template_question = form.save(commit=False)
            template_question.template = template
            
            # Check if question already exists
            if TemplateQuestion.objects.filter(
                template=template,
                question=template_question.question
            ).exists():
                messages.error(request, 'This question is already in the template!')
            else:
                template_question.save()
                messages.success(request, 'Question added to template successfully!')
            
            return redirect('inspections:template_detail', pk=template.pk)
    else:
        form = TemplateQuestionForm()
        
        # Exclude questions already in template
        existing_question_ids = template.template_questions.values_list('question_id', flat=True)
        form.fields['question'].queryset = InspectionQuestion.objects.filter(
            is_active=True
        ).exclude(id__in=existing_question_ids)
    
    context = {
        'form': form,
        'template': template,
        'title': f'Add Question to {template.template_name}'
    }
    return render(request, 'inspections/template_add_question.html', context)


@login_required
def template_bulk_add_questions(request, pk):
    """Bulk add questions to template"""
    
    template = get_object_or_404(InspectionTemplate, pk=pk)
    
    if request.method == 'POST':
        # Get selected question IDs from form
        question_ids = request.POST.getlist('questions')
        section_name = request.POST.get('section_name', '').strip()
        is_mandatory = request.POST.get('is_mandatory') == 'on'
        
        if not question_ids:
            messages.error(request, 'Please select at least one question!')
            return redirect('inspections:template_bulk_add_questions', pk=pk)
        
        # Get current max display order
        max_order = TemplateQuestion.objects.filter(
            template=template
        ).aggregate(
            max_order=models.Max('display_order')
        )['max_order'] or 0
        
        # Add selected questions
        added_count = 0
        for question_id in question_ids:
            try:
                question = InspectionQuestion.objects.get(pk=question_id, is_active=True)
                
                # Check if question already exists in template
                if TemplateQuestion.objects.filter(
                    template=template,
                    question=question
                ).exists():
                    continue
                
                # Create new template question
                max_order += 1
                TemplateQuestion.objects.create(
                    template=template,
                    question=question,
                    display_order=max_order,
                    section_name=section_name if section_name else None,
                    is_mandatory=is_mandatory
                )
                added_count += 1
                
            except InspectionQuestion.DoesNotExist:
                continue
        
        if added_count > 0:
            messages.success(
                request,
                f'{added_count} question(s) added to template successfully!'
            )
        else:
            messages.warning(request, 'No new questions were added. They may already be in the template.')
        
        return redirect('inspections:template_detail', pk=template.pk)
    
    # GET request - show selection form
    
    # Get questions NOT already in this template
    existing_question_ids = TemplateQuestion.objects.filter(
        template=template
    ).values_list('question_id', flat=True)
    
    # Get all active categories
    categories = InspectionCategory.objects.filter(
        is_active=True
    ).order_by('display_order')
    
    # Filter by category if selected
    selected_category = request.GET.get('category')
    
    available_questions = InspectionQuestion.objects.filter(
        is_active=True
    ).exclude(
        id__in=existing_question_ids
    ).select_related('category').order_by('category__display_order', 'display_order')
    
    if selected_category:
        available_questions = available_questions.filter(category_id=selected_category)
    
    context = {
        'template': template,
        'categories': categories,
        'available_questions': available_questions,
        'selected_category': selected_category,
        'title': f'Bulk Add Questions to {template.template_name}'
    }
    return render(request, 'inspections/template_bulk_add_questions.html', context)



@login_required
def template_remove_question(request, template_pk, question_pk):
    """Remove question from template"""
    
    template = get_object_or_404(InspectionTemplate, pk=template_pk)
    template_question = get_object_or_404(
        TemplateQuestion,
        template=template,
        question_id=question_pk
    )
    
    if request.method == 'POST':
        question_code = template_question.question.question_code
        template_question.delete()
        messages.success(request, f'Question {question_code} removed from template!')
        return redirect('inspections:template_detail', pk=template.pk)
    
    context = {
        'template': template,
        'template_question': template_question
    }
    return render(request, 'inspections/template_remove_question.html', context)


@login_required
def template_reorder_questions(request, pk):
    """AJAX endpoint to reorder questions in template"""
    
    if request.method == 'POST':
        import json
        
        template = get_object_or_404(InspectionTemplate, pk=pk)
        data = json.loads(request.body)
        
        for item in data:
            template_question = TemplateQuestion.objects.get(
                template=template,
                id=item['id']
            )
            template_question.display_order = item['order']
            template_question.save()
        
        return JsonResponse({'status': 'success', 'message': 'Questions reordered successfully'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def template_clone(request, pk):
    """Clone/duplicate a template"""
    
    original_template = get_object_or_404(InspectionTemplate, pk=pk)
    
    if request.method == 'POST':
        # Create new template
        new_template = InspectionTemplate.objects.create(
            template_name=f"{original_template.template_name} (Copy)",
            template_code=f"{original_template.template_code}-COPY",
            inspection_type=original_template.inspection_type,
            description=original_template.description,
            requires_approval=original_template.requires_approval,
            min_compliance_score=original_template.min_compliance_score,
            created_by=request.user
        )
        
        # Copy applicable plants and departments
        new_template.applicable_plants.set(original_template.applicable_plants.all())
        new_template.applicable_departments.set(original_template.applicable_departments.all())
        
        # Copy all questions
        for tq in original_template.template_questions.all():
            TemplateQuestion.objects.create(
                template=new_template,
                question=tq.question,
                is_mandatory=tq.is_mandatory,
                display_order=tq.display_order,
                section_name=tq.section_name
            )
        
        messages.success(request, f'Template cloned successfully as "{new_template.template_name}"!')
        return redirect('inspections:template_detail', pk=new_template.pk)
    
    context = {
        'template': original_template
    }
    return render(request, 'inspections/template_clone.html', context)


# ====================================
# SCHEDULE VIEWS
# ====================================

@login_required
def schedule_list(request):
    """List all inspection schedules"""
    
    schedules = InspectionSchedule.objects.select_related(
        'template',
        'assigned_to',
        'assigned_by',
        'plant',
        'department'
    )
    
    # User-based filtering
    if not request.user.is_superuser:
        if request.user.has_permission('CONDUCT_INSPECTION'):
            # HOD sees only their assigned inspections
            schedules = schedules.filter(assigned_to=request.user)
        elif request.user.can_access_inspection_module or request.user.is_plant_head:
            # Safety manager/plant head sees their plant's inspections
            user_plants = request.user.get_all_plants()
            schedules = schedules.filter(plant__in=user_plants)
    
    # Filters
    status = request.GET.get('status')
    plant_id = request.GET.get('plant')
    assigned_to_id = request.GET.get('assigned_to')
    search = request.GET.get('search')
    
    if status:
        schedules = schedules.filter(status=status)
    
    if plant_id:
        schedules = schedules.filter(plant_id=plant_id)
    
    if assigned_to_id:
        schedules = schedules.filter(assigned_to_id=assigned_to_id)
    
    if search:
        schedules = schedules.filter(
            Q(schedule_code__icontains=search) |
            Q(template__template_name__icontains=search) |
            Q(assigned_to__first_name__icontains=search) |
            Q(assigned_to__last_name__icontains=search)
        )
    
    schedules = schedules.order_by('-scheduled_date', '-created_at')
    
    # Pagination
    paginator = Paginator(schedules, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # For filters
    from apps.organizations.models import Plant
    plants = Plant.objects.filter(is_active=True)
    
    # Get HODs for filter
    hods = User.objects.filter(
        role__name='HOD',
        is_active_employee=True
    ).order_by('first_name', 'last_name')
    
    context = {
        'page_obj': page_obj,
        'status_choices': InspectionSchedule.STATUS_CHOICES,
        'plants': plants,
        'hods': hods,
        'selected_status': status,
        'selected_plant': plant_id,
        'selected_hod': assigned_to_id,
        'search': search
    }
    return render(request, 'inspections/schedule_list.html', context)


@login_required
def schedule_create(request):
    """Create new inspection schedule"""
    
    if request.method == 'POST':
        form = InspectionScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.assigned_by = request.user
            schedule.save()
            
            # Send notification email
            # send_inspection_assignment_email(schedule)
            NotificationService.notify(
                content_object=schedule,
                notification_type='INSPECTION_SCHEDULE',
                module='INSPECTION'
            )
            
            messages.success(
                request,
                f'Inspection scheduled successfully! Schedule Code: {schedule.schedule_code}'
            )
            return redirect('inspections:schedule_list')
    else:
        form = InspectionScheduleForm(user=request.user)
        
        # Pre-fill plant if user has only one
        if not request.user.is_superuser:
            user_plants = request.user.get_all_plants()
            if len(user_plants) == 1:
                form.initial['plant'] = user_plants[0]
    
    context = {
        'form': form,
        'action': 'Create',
        'title': 'Schedule New Inspection'
    }
    return render(request, 'inspections/schedule_form.html', context)


@login_required
def schedule_edit(request, pk):
    """Edit inspection schedule"""
    
    schedule = get_object_or_404(InspectionSchedule, pk=pk)
    
    # Check permissions
    if not request.user.is_superuser:
        if schedule.status in ['COMPLETED', 'CANCELLED']:
            messages.error(request, 'Cannot edit completed or cancelled inspections!')
            return redirect('inspections:schedule_detail', pk=pk)
    
    if request.method == 'POST':
        form = InspectionScheduleForm(request.POST, instance=schedule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inspection schedule updated successfully!')
            return redirect('inspections:schedule_detail', pk=pk)
    else:
        form = InspectionScheduleForm(instance=schedule, user=request.user)
    
    context = {
        'form': form,
        'action': 'Edit',
        'title': f'Edit Schedule: {schedule.schedule_code}',
        'schedule': schedule
    }
    return render(request, 'inspections/schedule_form.html', context)


@login_required
def schedule_detail(request, pk):
    """View schedule details"""
    
    schedule = get_object_or_404(
        InspectionSchedule.objects.select_related(
            'template',
            'assigned_to',
            'assigned_by',
            'plant',
            'zone',
            'location',
            'sublocation',
            'department'
        ),
        pk=pk
    )
    
    # Check access
    if not request.user.is_superuser:
        if request.user.has_permission('VIEW_INSPECTION') and schedule.assigned_to != request.user:
            messages.error(request, 'You do not have permission to view this inspection!')
            return redirect('inspections:schedule_list')
    
    context = {
        'schedule': schedule,
        'can_edit': schedule.status not in ['COMPLETED', 'CANCELLED'],
        'can_start': schedule.status == 'SCHEDULED' and schedule.assigned_to == request.user,
        'can_cancel': schedule.status not in ['COMPLETED', 'CANCELLED']
    }
    return render(request, 'inspections/schedule_detail.html', context)


@login_required
def schedule_cancel(request, pk):
    """Cancel inspection schedule"""
    
    schedule = get_object_or_404(InspectionSchedule, pk=pk)
    
    if schedule.status in ['COMPLETED', 'CANCELLED']:
        messages.error(request, 'Cannot cancel completed or already cancelled inspections!')
        return redirect('inspections:schedule_detail', pk=pk)
    
    if request.method == 'POST':
        schedule.status = 'CANCELLED'
        schedule.save()
        
        messages.success(request, f'Inspection {schedule.schedule_code} cancelled successfully!')
        return redirect('inspections:schedule_list')
    
    context = {
        'schedule': schedule
    }
    return render(request, 'inspections/schedule_cancel.html', context)


@login_required
def schedule_send_reminder(request, pk):
    """Send reminder for scheduled inspection"""
    
    schedule = get_object_or_404(InspectionSchedule, pk=pk)
    
    if schedule.status not in ['SCHEDULED', 'IN_PROGRESS']:
        messages.error(request, 'Can only send reminders for scheduled or in-progress inspections!')
        return redirect('inspections:schedule_detail', pk=pk)
    
    # Send reminder email
    # send_inspection_reminder_email(schedule)
    
    schedule.reminder_sent = True
    schedule.reminder_sent_at = timezone.now()
    schedule.save()

    NotificationService.notify(
        content_object=schedule,
        notification_type='NOTIFY_INSPECTION',
        module='INSPECTION'
    )
    
    messages.success(request, f'Reminder sent to {schedule.assigned_to.get_full_name()}!')
    return redirect('inspections:schedule_detail', pk=pk)


@login_required
def my_inspections(request):
    """View for HOD to see their assigned inspections"""
    
    if not request.user.has_permission('VIEW_INSPECTION'):
        messages.error(request, 'This page is only for HODs!')
        return redirect('inspections:inspection_dashboard')
    
    schedules = InspectionSchedule.objects.filter(
        assigned_to=request.user
    ).select_related('template', 'plant', 'department')
    
    # Filters
    status = request.GET.get('status', 'SCHEDULED')
    if status:
        schedules = schedules.filter(status=status)
    
    schedules = schedules.order_by('-scheduled_date')
    
    # Pagination
    paginator = Paginator(schedules, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Stats
    stats = {
        'scheduled': InspectionSchedule.objects.filter(
            assigned_to=request.user,
            status='SCHEDULED'
        ).count(),
        'in_progress': InspectionSchedule.objects.filter(
            assigned_to=request.user,
            status='IN_PROGRESS'
        ).count(),
        'completed': InspectionSchedule.objects.filter(
            assigned_to=request.user,
            status='COMPLETED'
        ).count(),
        'overdue': InspectionSchedule.objects.filter(
            assigned_to=request.user,
            status='OVERDUE'
        ).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'selected_status': status,
        'status_choices': InspectionSchedule.STATUS_CHOICES
    }
    return render(request, 'inspections/my_inspections.html', context)


########################inspection start ###################################
@login_required
def inspection_start(request, schedule_id):
    """HOD starts filling the inspection"""
    
    schedule = get_object_or_404(InspectionSchedule, pk=schedule_id)
    
    # Check permission - only assigned HOD can start
    if schedule.assigned_to != request.user:
        messages.error(request, 'You are not authorized to access this inspection!')
        return redirect('inspections:my_inspections')
    
    # Check if already completed
    if schedule.status == 'COMPLETED':
        messages.warning(request, 'This inspection is already completed!')
        return redirect('inspections:schedule_detail', pk=schedule.pk)
    
    # Update status to IN_PROGRESS
    if schedule.status == 'SCHEDULED':
        schedule.status = 'IN_PROGRESS'
        schedule.started_at = timezone.now()
        schedule.save()
    
    # Get all questions from template in order
    template_questions = TemplateQuestion.objects.filter(
        template=schedule.template
    ).select_related(
        'question',
        'question__category'
    ).order_by('display_order')
    
    # Group questions by category
    from collections import defaultdict
    questions_by_category = defaultdict(list)
    
    for tq in template_questions:
        questions_by_category[tq.question.category].append(tq)
    
    # Sort by category display order
    questions_by_category = dict(sorted(
        questions_by_category.items(),
        key=lambda x: x[0].display_order
    ))
    
    context = {
        'schedule': schedule,
        'questions_by_category': questions_by_category,
        'total_questions': template_questions.count()
    }
    
    return render(request, 'inspections/inspection_form.html', context)



def generate_finding_code(submission):
    """Generate unique finding code"""
    from datetime import datetime
    date_str = datetime.now().strftime('%Y%m')
    
    last_finding = InspectionFinding.objects.filter(
        finding_code__startswith=f"FIND-{date_str}"
    ).order_by('-finding_code').first()
    
    if last_finding:
        try:
            last_num = int(last_finding.finding_code.split('-')[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1
    
    return f"FIND-{date_str}-{new_num:04d}"
@login_required
def inspection_submit(request, schedule_id):
    """HOD submits the completed inspection"""
    
    schedule = get_object_or_404(InspectionSchedule, pk=schedule_id)
    
    # Check permission
    if schedule.assigned_to != request.user:
        messages.error(request, 'Unauthorized access!')
        return redirect('inspections:my_inspections')
    
    if request.method == 'POST':
        # Create submission record
        submission = InspectionSubmission.objects.create(
            schedule=schedule,
            submitted_by=request.user,
            remarks=request.POST.get('overall_remarks', '')
        )
        
        # Process each question response
        template_questions = TemplateQuestion.objects.filter(
            template=schedule.template
        ).select_related('question')
        
        no_answers = []  # Track questions answered "No"
        
        for tq in template_questions:
            question = tq.question
            field_name = f"question_{question.id}"
            
            # Get answer
            answer = request.POST.get(field_name)
            remarks = request.POST.get(f"remarks_{question.id}", '')
            
            # Handle photo upload if exists
            photo = request.FILES.get(f"photo_{question.id}")
            
            # Save response
            response = InspectionResponse.objects.create(
                submission=submission,
                question=question,
                answer=answer,
                remarks=remarks,
                photo=photo
            )
            
            # Track "No" answers
            if answer == 'No':
                no_answers.append({
                    'question': question,
                    'response': response
                })
                
                # Auto-generate finding if configured
                if question.auto_generate_finding:
                    InspectionFinding.objects.create(
                        submission=submission,
                        question=question,
                        finding_code=generate_finding_code(submission),
                        description=f"Non-compliance found: {question.question_text}",
                        priority='HIGH' if question.is_critical else 'MEDIUM',
                        status='OPEN'
                    )
        
        # Calculate compliance score
        submission.compliance_score = submission.calculate_compliance_score()
        submission.save()
        
        # Update schedule status
        schedule.status = 'COMPLETED'
        schedule.completed_at = timezone.now()
        schedule.save()
        
        # Send notification about completion
        NotificationService.notify(
            content_object=submission,
            notification_type='INSPECTION_COMPLETED',
            module='INSPECTION'
        )
        
        messages.success(
            request,
            f'Inspection {schedule.schedule_code} submitted successfully! '
            f'Compliance Score: {submission.compliance_score}%'
        )
        
        # Redirect to review page showing "No" answers
        return redirect('inspections:inspection_review', submission_id=submission.id)
    
    return redirect('inspections:inspection_start', schedule_id=schedule_id)


@login_required
def inspection_review(request, submission_id):
    """Review completed inspection showing all "No" answers"""
    
    submission = get_object_or_404(
        InspectionSubmission.objects.select_related(
            'schedule',
            'schedule__template',
            'schedule__plant',
            'submitted_by'
        ),
        pk=submission_id
    )
    
    # Check permission
    if not (request.user.is_superuser or 
            request.user == submission.submitted_by or
            request.user.can_access_inspection_module):
        messages.error(request, 'Unauthorized access!')
        return redirect('inspections:inspection_dashboard')
    
    # Get all "No" answers
    no_responses = InspectionResponse.objects.filter(
        submission=submission,
        answer='No'
    ).select_related(
        'question',
        'question__category'
    ).order_by('question__category__display_order', 'question__display_order')
    
    # Group by category
    from collections import defaultdict
    no_answers_by_category = defaultdict(list)
    
    for response in no_responses:
        no_answers_by_category[response.question.category].append(response)
    
    # Get all findings for this submission
    findings = InspectionFinding.objects.filter(
        submission=submission
    ).select_related('question', 'assigned_to')
    
    # Get all responses for statistics
    all_responses = submission.responses.all()
    total_questions = all_responses.count()
    yes_count = all_responses.filter(answer='Yes').count()
    no_count = all_responses.filter(answer='No').count()
    na_count = all_responses.filter(answer='N/A').count()
    
    context = {
        'submission': submission,
        'schedule': submission.schedule,
        'no_answers_by_category': dict(no_answers_by_category),
        'findings': findings,
        'total_questions': total_questions,
        'yes_count': yes_count,
        'no_count': no_count,
        'na_count': na_count,
        'compliance_score': submission.compliance_score,
    }
    
    return render(request, 'inspections/inspection_review.html', context)

# ====================================
# AJAX/API ENDPOINTS
# ====================================

@login_required
def get_zones_by_plant(request):
    """AJAX: Get zones for selected plant"""
    
    plant_id = request.GET.get('plant_id')
    
    if not plant_id:
        return JsonResponse({'zones': []})
    
    from apps.organizations.models import Zone
    zones = Zone.objects.filter(plant_id=plant_id, is_active=True).values('id', 'name')
    
    return JsonResponse({'zones': list(zones)})


@login_required
def get_locations_by_zone(request):
    """AJAX: Get locations for selected zone"""
    
    zone_id = request.GET.get('zone_id')
    
    if not zone_id:
        return JsonResponse({'locations': []})
    
    from apps.organizations.models import Location
    locations = Location.objects.filter(zone_id=zone_id, is_active=True).values('id', 'name')
    
    return JsonResponse({'locations': list(locations)})


@login_required
def get_sublocations_by_location(request):
    """AJAX: Get sublocations for selected location"""
    
    location_id = request.GET.get('location_id')
    
    if not location_id:
        return JsonResponse({'sublocations': []})
    
    from apps.organizations.models import SubLocation
    sublocations = SubLocation.objects.filter(
        location_id=location_id,
        is_active=True
    ).values('id', 'name')
    
    return JsonResponse({'sublocations': list(sublocations)})


@login_required
def get_questions_by_category(request):
    """AJAX: Get questions for selected category"""
    
    category_id = request.GET.get('category_id')
    template_id = request.GET.get('template_id')
    
    if not category_id:
        return JsonResponse({'questions': []})
    
    questions = InspectionQuestion.objects.filter(
        category_id=category_id,
        is_active=True
    )
    
    # Exclude questions already in template
    if template_id:
        existing_question_ids = TemplateQuestion.objects.filter(
            template_id=template_id
        ).values_list('question_id', flat=True)
        questions = questions.exclude(id__in=existing_question_ids)
    
    questions_data = questions.values('id', 'question_code', 'question_text')
    
    return JsonResponse({'questions': list(questions_data)})



@login_required
def no_answers_list(request):
    """
    Separate page showing all questions answered 'No' 
    across all inspections with filters
    """
    
    # Base queryset - all "No" responses
    no_responses = InspectionResponse.objects.filter(
        answer='No'
    ).select_related(
        'submission',
        'submission__schedule',
        'submission__schedule__plant',
        'submission__schedule__assigned_to',
        'submission__submitted_by',
        'question',
        'question__category'
    )
    
    # Apply user-based filtering
    if not request.user.is_superuser:
        if request.user.has_permission('VIEW_INSPECTION'):
            # HOD sees only their submissions
            no_responses = no_responses.filter(
                submission__submitted_by=request.user
            )
        elif request.user.can_access_inspection_module:
            # Safety officer sees their plant's submissions
            user_plants = request.user.get_all_plants()
            no_responses = no_responses.filter(
                submission__schedule__plant__in=user_plants
            )
    
    # Filters
    plant_id = request.GET.get('plant')
    category_id = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    priority = request.GET.get('priority')  # critical or normal
    search = request.GET.get('search')
    
    if plant_id:
        no_responses = no_responses.filter(
            submission__schedule__plant_id=plant_id
        )
    
    if category_id:
        no_responses = no_responses.filter(
            question__category_id=category_id
        )
    
    if date_from:
        no_responses = no_responses.filter(
            answered_at__gte=date_from
        )
    
    if date_to:
        no_responses = no_responses.filter(
            answered_at__lte=date_to
        )
    
    if priority == 'critical':
        no_responses = no_responses.filter(
            question__is_critical=True
        )
    
    if search:
        no_responses = no_responses.filter(
            Q(question__question_text__icontains=search) |
            Q(question__question_code__icontains=search) |
            Q(remarks__icontains=search)
        )
    
    no_responses = no_responses.order_by('-answered_at')
    
    # Statistics
    total_no_answers = no_responses.count()
    critical_no_answers = no_responses.filter(question__is_critical=True).count()
    
    # Group by category for summary
    from django.db.models import Count
    category_summary = no_responses.values(
        'question__category__category_name',
        'question__category__id'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Pagination
    paginator = Paginator(no_responses, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # For filters
    from apps.organizations.models import Plant
    plants = Plant.objects.filter(is_active=True)
    categories = InspectionCategory.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'total_no_answers': total_no_answers,
        'critical_no_answers': critical_no_answers,
        'category_summary': category_summary,
        'plants': plants,
        'categories': categories,
        'selected_plant': plant_id,
        'selected_category': category_id,
        'date_from': date_from,
        'date_to': date_to,
        'selected_priority': priority,
        'search': search,
    }
    
    return render(request, 'inspections/no_answers_list.html', context)


@login_required
def no_answers_by_question(request):
    """
    Show aggregated view: which questions get 'No' most frequently
    """
    
    # Get all "No" responses grouped by question
    from django.db.models import Count
    
    question_stats = InspectionResponse.objects.filter(
        answer='No'
    ).values(
        'question__id',
        'question__question_code',
        'question__question_text',
        'question__category__category_name',
        'question__is_critical'
    ).annotate(
        no_count=Count('id')
    ).order_by('-no_count')
    
    # Apply filters if needed
    category_id = request.GET.get('category')
    if category_id:
        question_stats = question_stats.filter(
            question__category_id=category_id
        )
    
    # Pagination
    paginator = Paginator(question_stats, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = InspectionCategory.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id,
    }
    
    return render(request, 'inspections/no_answers_by_question.html', context)


# Add to apps/inspections/views.py

@login_required
def convert_no_answer_to_hazard(request, response_id):
    """
    Convert an inspection 'No' answer into a hazard report
    """
    from apps.hazards.models import Hazard, HazardPhoto
    from django.utils import timezone
    
    # Get the response
    response = get_object_or_404(
        InspectionResponse.objects.select_related(
            'submission',
            'submission__schedule',
            'submission__schedule__plant',
            'submission__schedule__zone',
            'submission__schedule__location',
            'submission__schedule__sublocation',
            'question',
            'question__category'
        ),
        pk=response_id,
        answer='No'  # Only allow 'No' answers
    )
    
    # Check if already converted
    if response.converted_to_hazard:
        messages.warning(
            request,
            f'This inspection item has already been converted to Hazard: {response.converted_to_hazard.report_number}'
        )
        return redirect('inspections:inspection_review', submission_id=response.submission.id)
    
    # Check permission
    if not (request.user.is_superuser or 
            request.user.can_access_inspection_module or
            request.user == response.submission.submitted_by):
        messages.error(request, 'Unauthorized access!')
        return redirect('inspections:inspection_dashboard')
    
    if request.method == 'POST':
        try:
            schedule = response.submission.schedule
            
            # Create hazard
            hazard = Hazard()
            
            # Reporter information (from inspection submitter)
            hazard.reported_by = response.submission.submitted_by
            hazard.reporter_name = response.submission.submitted_by.get_full_name()
            hazard.reporter_email = response.submission.submitted_by.email
            hazard.reporter_phone = getattr(response.submission.submitted_by, 'phone', '')
            
            # Hazard type and category mapping from inspection
            hazard.hazard_type = request.POST.get('hazard_type', 'UC')  # Default to Unsafe Condition
            
            # Map inspection category to hazard category
            hazard.hazard_category = request.POST.get('hazard_category', 'other')
            
            # Severity from form or auto-determine
            hazard.severity = request.POST.get('severity')
            if not hazard.severity:
                # Auto-determine from inspection question
                if response.question.is_critical:
                    hazard.severity = 'high'
                else:
                    hazard.severity = 'medium'
            
            # Location information from schedule
            hazard.plant = schedule.plant
            hazard.zone = schedule.zone
            hazard.location = schedule.location
            hazard.sublocation = schedule.sublocation
            
            # Hazard details
            category_name = response.question.category.category_name
            hazard.hazard_title = f"Inspection Non-Compliance: {category_name} - {response.question.question_code}"
            
            # Description combines question and remarks
            description_parts = [
                f"**Source:** Inspection {schedule.schedule_code}",
                f"**Question:** {response.question.question_text}",
                f"**Category:** {category_name}",
            ]
            
            if response.question.reference_standard:
                description_parts.append(f"**Standard:** {response.question.reference_standard}")
            
            if response.remarks:
                description_parts.append(f"**Inspector Remarks:** {response.remarks}")
            else:
                description_parts.append("**Inspector Remarks:** No remarks provided")
            
            hazard.hazard_description = "\n\n".join(description_parts)
            
            # Additional details from form
            hazard.immediate_action = request.POST.get('immediate_action', '')
            
            # Incident datetime
            hazard.incident_datetime = response.answered_at or schedule.completed_at or timezone.now()
            
            # Status
            hazard.status = 'REPORTED'
            hazard.approval_status = 'PENDING'
            
            # Set deadline based on severity
            severity_days = {'low': 30, 'medium': 15, 'high': 7, 'critical': 1}
            hazard.action_deadline = timezone.now().date() + timezone.timedelta(
                days=severity_days.get(hazard.severity, 15)
            )
            
            # Save hazard
            hazard.save()
            
            # Generate report number
            today = timezone.now().date()
            plant_code = hazard.plant.code if hazard.plant else 'UNKN'
            count = Hazard.objects.filter(created_at__date=today).count()
            hazard.report_number = f"HAZ-{plant_code}-{today:%Y%m%d}-{count:03d}"
            hazard.save(update_fields=['report_number'])
            
            # Copy photo if exists
            if response.photo:
                try:
                    HazardPhoto.objects.create(
                        hazard=hazard,
                        photo=response.photo,
                        photo_type='evidence',
                        description=f'Photo from inspection {schedule.schedule_code}',
                        uploaded_by=request.user
                    )
                except Exception as e:
                    print(f"Error copying photo: {e}")
            
            # Link response to hazard
            response.converted_to_hazard = hazard
            response.save(update_fields=['converted_to_hazard'])
            
            # Send notifications
            try:
                NotificationService.notify(
                    content_object=hazard,
                    notification_type='HAZARD_REPORTED',
                    module='HAZARD'
                )
            except Exception as e:
                print(f"Notification error: {e}")
            
            messages.success(
                request,
                mark_safe(
                    f'<strong>✅ Hazard Created from Inspection!</strong><br>'
                    f'Report No: <strong>{hazard.report_number}</strong><br>'
                    f'Source: Inspection {schedule.schedule_code}<br>'
                    f'Severity: {hazard.get_severity_display()}'
                )
            )
            
            return redirect('hazards:hazard_detail', pk=hazard.pk)
            
        except Exception as e:
            print(f"Error converting to hazard: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error creating hazard: {str(e)}')
            return redirect('inspections:inspection_review', submission_id=response.submission.id)
    
    # GET request - show confirmation form
    context = {
        'response': response,
        'question': response.question,
        'submission': response.submission,
        'schedule': response.submission.schedule,
        'hazard_types': Hazard.HAZARD_TYPE_CHOICES,
        'hazard_categories': Hazard.HAZARD_CATEGORIES,
        'severity_choices': Hazard.SEVERITY_CHOICES,
        'auto_severity': 'high' if response.question.is_critical else 'medium',
    }
    
    return render(request, 'inspections/convert_to_hazard.html', context)


    