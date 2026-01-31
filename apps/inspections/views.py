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
        if request.user.is_hod:
            # HOD sees their assigned inspections
            context['my_pending_inspections'] = InspectionSchedule.objects.filter(
                assigned_to=request.user,
                status__in=['SCHEDULED', 'IN_PROGRESS']
            ).count()
            context['my_overdue_inspections'] = InspectionSchedule.objects.filter(
                assigned_to=request.user,
                status='OVERDUE'
            ).count()
        
        elif request.user.is_safety_manager or request.user.is_superuser:
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
        if request.user.is_hod:
            # HOD sees only their assigned inspections
            schedules = schedules.filter(assigned_to=request.user)
        elif request.user.is_safety_manager or request.user.is_plant_head:
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
            send_inspection_assignment_email(schedule)
            
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
        if request.user.is_hod and schedule.assigned_to != request.user:
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
    send_inspection_reminder_email(schedule)
    
    schedule.reminder_sent = True
    schedule.reminder_sent_at = timezone.now()
    schedule.save()
    
    messages.success(request, f'Reminder sent to {schedule.assigned_to.get_full_name()}!')
    return redirect('inspections:schedule_detail', pk=pk)


@login_required
def my_inspections(request):
    """View for HOD to see their assigned inspections"""
    
    if not request.user.is_hod:
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


@login_required
def inspection_submit(request, schedule_id):
    """HOD submits the completed inspection"""
    
    schedule = get_object_or_404(InspectionSchedule, pk=schedule_id)
    
    # Check permission
    if schedule.assigned_to != request.user:
        messages.error(request, 'Unauthorized access!')
        return redirect('inspections:my_inspections')
    
    if request.method == 'POST':
        # You'll implement submission logic here later
        # For now, just mark as completed
        
        schedule.status = 'COMPLETED'
        schedule.completed_at = timezone.now()
        schedule.save()
        
        messages.success(
            request,
            f'Inspection {schedule.schedule_code} submitted successfully!'
        )
        
        return redirect('inspections:my_inspections')
    
    return redirect('inspections:inspection_start', schedule_id=schedule_id)

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


# ====================================
# EMAIL NOTIFICATION FUNCTIONS
# ====================================

def send_inspection_assignment_email(schedule):
    """Send email notification when inspection is assigned"""
    
    from django.core.mail import send_mail
    from django.conf import settings
    from django.template.loader import render_to_string
    
    subject = f'New Inspection Assigned: {schedule.template.template_name}'
    
    context = {
        'schedule': schedule,
        'hod_name': schedule.assigned_to.get_full_name(),
        'safety_officer': schedule.assigned_by.get_full_name(),
        'template_name': schedule.template.template_name,
        'scheduled_date': schedule.scheduled_date,
        'due_date': schedule.due_date,
        'plant': schedule.plant.name,
    }
    
    # HTML email
    html_message = render_to_string('emails/inspection/inspection_assigned.html', context)
    
    # Plain text fallback
    plain_message = f"""
    Dear {context['hod_name']},
    
    You have been assigned a new inspection:
    
    Template: {context['template_name']}
    Scheduled Date: {context['scheduled_date']}
    Due Date: {context['due_date']}
    Plant: {context['plant']}
    
    Please complete this inspection before the due date.
    
    Best regards,
    EHS-360 Team
    """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[schedule.assigned_to.email],
            html_message=html_message,
            fail_silently=False
        )
    except Exception as e:
        print(f"Error sending email: {e}")


def send_inspection_reminder_email(schedule):
    """Send reminder email for pending inspection"""
    
    from django.core.mail import send_mail
    from django.conf import settings
    
    subject = f'Reminder: Pending Inspection - {schedule.template.template_name}'
    
    message = f"""
    Dear {schedule.assigned_to.get_full_name()},
    
    This is a reminder for your pending inspection:
    
    Schedule Code: {schedule.schedule_code}
    Template: {schedule.template.template_name}
    Due Date: {schedule.due_date}
    Status: {schedule.get_status_display()}
    
    Please complete this inspection as soon as possible.
    
    Best regards,
    EHS-360 Team
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[schedule.assigned_to.email],
            fail_silently=False
        )
    except Exception as e:
        print(f"Error sending reminder email: {e}")


        