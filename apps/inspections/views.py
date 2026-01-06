# apps/inspections/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
import json

from .models import (
    InspectionTemplate, InspectionCategory, InspectionPoint,
    InspectionSchedule, Inspection, InspectionResponse,
    InspectionFinding, InspectionAttachment
)
from .forms import (
    InspectionScheduleForm, InspectionForm, InspectionResponseForm,
    FindingAssignmentForm, FindingActionForm, FindingClosureForm,
    InspectionTemplateForm, InspectionCategoryForm, InspectionPointForm,
    InspectionFilterForm, FindingFilterForm
)
from apps.organizations.models import Plant, Location
from apps.accounts.models import User


# ========================================
# DASHBOARD VIEWS
# ========================================

@login_required
def inspection_dashboard(request):
    """Main inspection dashboard with statistics and charts"""
    
    # Base queryset based on user role
    if request.user.is_superuser or request.user.role == 'ADMIN':
        schedules = InspectionSchedule.objects.all()
        inspections = Inspection.objects.all()
        findings = InspectionFinding.objects.all()
    elif request.user.plant:
        schedules = InspectionSchedule.objects.filter(plant=request.user.plant)
        inspections = Inspection.objects.filter(plant=request.user.plant)
        findings = InspectionFinding.objects.filter(inspection__plant=request.user.plant)
    else:
        schedules = InspectionSchedule.objects.none()
        inspections = Inspection.objects.none()
        findings = InspectionFinding.objects.none()
    
    # Statistics
    stats = {
        'scheduled_count': schedules.filter(status='SCHEDULED').count(),
        'pending_count': schedules.filter(status='IN_PROGRESS').count(),
        'completed_count': inspections.filter(
            status='SUBMITTED',
            inspection_date__month=timezone.now().month,
            inspection_date__year=timezone.now().year
        ).count(),
        'overdue_count': schedules.filter(status='OVERDUE').count(),
        'avg_compliance_score': inspections.aggregate(Avg('overall_score'))['overall_score__avg'] or 0,
    }
    
    # Findings statistics
    findings_stats = {
        'open_count': findings.filter(status='OPEN').count(),
        'in_progress_count': findings.filter(status='IN_PROGRESS').count(),
        'closed_count': findings.filter(status='CLOSED').count(),
    }
    
    # Recent inspections
    recent_inspections = inspections.select_related(
        'template', 'plant', 'location', 'conducted_by'
    ).order_by('-inspection_date')[:10]
    
    # My assigned inspections (for HOD)
    my_assigned_inspections = []
    if request.user.role == 'HOD':
        my_assigned_inspections = schedules.filter(
            assigned_to=request.user,
            status__in=['SCHEDULED', 'IN_PROGRESS', 'OVERDUE']
        ).select_related('template', 'plant').order_by('due_date')[:5]
    
    # Monthly trend data (last 6 months)
    monthly_labels = []
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = timezone.now() - timedelta(days=30*i)
        month_name = month_date.strftime('%b')
        monthly_labels.append(month_name)
        
        count = inspections.filter(
            inspection_date__month=month_date.month,
            inspection_date__year=month_date.year,
            status='SUBMITTED'
        ).count()
        monthly_data.append(count)
    
    context = {
        'stats': stats,
        'findings_stats': findings_stats,
        'recent_inspections': recent_inspections,
        'my_assigned_inspections': my_assigned_inspections,
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_data),
    }
    
    return render(request, 'inspections/inspection_dashboard.html', context)


# ========================================
# INSPECTION SCHEDULE VIEWS
# ========================================

@login_required
def schedule_list(request):
    """List all inspection schedules"""
    
    # Base queryset
    if request.user.is_superuser or request.user.role == 'ADMIN':
        schedules = InspectionSchedule.objects.all()
    elif request.user.plant:
        schedules = InspectionSchedule.objects.filter(plant=request.user.plant)
    else:
        schedules = InspectionSchedule.objects.none()
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        schedules = schedules.filter(status=status_filter)
    
    # Filter for user's assigned schedules
    if request.user.role == 'HOD':
        schedules = schedules.filter(assigned_to=request.user)
    
    schedules = schedules.select_related(
        'template', 'plant', 'zone', 'location', 'assigned_to'
    ).order_by('-due_date')
    
    context = {
        'schedules': schedules,
        'status_filter': status_filter,
    }
    
    return render(request, 'inspections/schedule_list.html', context)


@login_required
def schedule_create(request):
    """Create new inspection schedule (Safety Officer only)"""
    
    # Check permission
    if not (request.user.is_superuser or request.user.role in ['ADMIN', 'SAFETY_MANAGER']):
        messages.error(request, 'You do not have permission to schedule inspections.')
        return redirect('inspections:dashboard')
    
    if request.method == 'POST':
        form = InspectionScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.assigned_by = request.user
            schedule.save()
            
            messages.success(
                request,
                f'Inspection scheduled successfully for {schedule.assigned_to.get_full_name()}.'
            )
            return redirect('inspections:schedule_list')
    else:
        form = InspectionScheduleForm(user=request.user)
    
    context = {
        'form': form,
    }
    
    return render(request, 'inspections/schedule_create.html', context)


# ========================================
# CONDUCT INSPECTION VIEWS
# ========================================

@login_required
def conduct_inspection(request, schedule_id):
    """Conduct inspection based on schedule"""
    
    schedule = get_object_or_404(InspectionSchedule, id=schedule_id)
    
    # Check permission
    if not (request.user.is_superuser or schedule.assigned_to == request.user):
        messages.error(request, 'You are not assigned to this inspection.')
        return redirect('inspections:schedule_list')
    
    # Get or create inspection
    inspection, created = Inspection.objects.get_or_create(
        inspection_schedule=schedule,
        defaults={
            'template': schedule.template,
            'plant': schedule.plant,
            'zone': schedule.zone,
            'location': schedule.location,
            'conducted_by': request.user,
            'inspection_date': timezone.now().date(),
            'department': request.user.department,
        }
    )
    
    # Get all categories and points for this template
    categories = InspectionCategory.objects.filter(
        template=schedule.template,
        is_active=True
    ).prefetch_related('inspection_points').order_by('sequence_order')
    
    total_points = InspectionPoint.objects.filter(
        category__template=schedule.template,
        is_active=True
    ).count()
    
    if request.method == 'POST':
        # Get JSON data from hidden field
        responses_json = request.POST.get('inspection_responses_json')
        save_as_draft = request.POST.get('save_as_draft') == 'true'
        
        if responses_json:
            try:
                responses_data = json.loads(responses_json)
                
                # Save each response
                for point_id, response_data in responses_data.items():
                    point = InspectionPoint.objects.get(id=int(point_id))
                    category = point.category
                    
                    # Create or update response
                    response, created = InspectionResponse.objects.update_or_create(
                        inspection=inspection,
                        inspection_point=point,
                        defaults={
                            'category': category,
                            'response': response_data.get('response'),
                            'remarks': response_data.get('remarks', ''),
                        }
                    )
                    
                    # Handle photo uploads
                    for i in range(1, 4):
                        photo_field = f'photo_{point_id}_{i}'
                        if photo_field in request.FILES:
                            setattr(response, f'photo_{i}', request.FILES[photo_field])
                    
                    response.save()
                
                # Update inspection status and scores
                if save_as_draft:
                    inspection.status = 'DRAFT'
                    schedule.status = 'IN_PROGRESS'
                    messages.success(request, 'Inspection saved as draft successfully.')
                else:
                    inspection.status = 'SUBMITTED'
                    inspection.submitted_at = timezone.now()
                    schedule.status = 'COMPLETED'
                    messages.success(request, 'Inspection submitted successfully!')
                
                # Calculate compliance score
                inspection.overall_score = inspection.calculate_compliance_score()
                inspection.save()
                schedule.save()
                
                # Generate PDF (implement later)
                # generate_inspection_pdf(inspection)
                
                return redirect('inspections:inspection_detail', pk=inspection.id)
                
            except Exception as e:
                messages.error(request, f'Error saving inspection: {str(e)}')
    
    context = {
        'schedule': schedule,
        'inspection': inspection,
        'template': schedule.template,
        'categories': categories,
        'total_points': total_points,
    }
    
    return render(request, 'inspections/conduct_inspection.html', context)


# ========================================
# INSPECTION LIST & DETAIL VIEWS
# ========================================

@login_required
def inspection_list(request):
    """List all inspections with filters"""
    
    # Base queryset
    if request.user.is_superuser or request.user.role == 'ADMIN':
        inspections = Inspection.objects.all()
    elif request.user.plant:
        inspections = Inspection.objects.filter(plant=request.user.plant)
    else:
        inspections = Inspection.objects.none()
    
    # Apply filters
    filter_form = InspectionFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('plant'):
            inspections = inspections.filter(plant=filter_form.cleaned_data['plant'])
        if filter_form.cleaned_data.get('template'):
            inspections = inspections.filter(template=filter_form.cleaned_data['template'])
        if filter_form.cleaned_data.get('status'):
            inspections = inspections.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('month'):
            inspections = inspections.filter(month=filter_form.cleaned_data['month'])
        if filter_form.cleaned_data.get('year'):
            inspections = inspections.filter(year=filter_form.cleaned_data['year'])
        if filter_form.cleaned_data.get('search'):
            search = filter_form.cleaned_data['search']
            inspections = inspections.filter(inspection_number__icontains=search)
    
    inspections = inspections.select_related(
        'template', 'plant', 'location', 'conducted_by'
    ).order_by('-inspection_date')
    
    context = {
        'inspections': inspections,
        'filter_form': filter_form,
    }
    
    return render(request, 'inspections/inspection_list.html', context)


@login_required
def inspection_detail(request, pk):
    """View inspection details"""
    
    inspection = get_object_or_404(
        Inspection.objects.select_related(
            'template', 'plant', 'zone', 'location', 'department', 'conducted_by'
        ),
        pk=pk
    )
    
    # Check permission
    if not (request.user.is_superuser or 
            inspection.plant == request.user.plant or
            inspection.conducted_by == request.user):
        messages.error(request, 'You do not have permission to view this inspection.')
        return redirect('inspections:inspection_list')
    
    # Get all responses grouped by category
    responses = inspection.responses.select_related(
        'category', 'inspection_point'
    ).order_by('category__sequence_order', 'sequence_order')
    
    # Get all findings
    findings = inspection.findings.select_related('assigned_to').order_by('-created_at')
    
    context = {
        'inspection': inspection,
        'responses': responses,
        'findings': findings,
    }
    
    return render(request, 'inspections/inspection_detail.html', context)


# ========================================
# FINDINGS VIEWS
# ========================================

@login_required
def findings_list(request):
    """List all inspection findings"""
    
    # Base queryset
    if request.user.is_superuser or request.user.role == 'ADMIN':
        findings = InspectionFinding.objects.all()
    elif request.user.plant:
        findings = InspectionFinding.objects.filter(inspection__plant=request.user.plant)
    else:
        findings = InspectionFinding.objects.none()
    
    # Apply filters
    filter_form = FindingFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('plant'):
            findings = findings.filter(inspection__plant=filter_form.cleaned_data['plant'])
        if filter_form.cleaned_data.get('status'):
            findings = findings.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('severity'):
            findings = findings.filter(severity=filter_form.cleaned_data['severity'])
        if filter_form.cleaned_data.get('assigned_to_me'):
            findings = findings.filter(assigned_to=request.user)
        if filter_form.cleaned_data.get('overdue_only'):
            findings = findings.filter(
                status__in=['OPEN', 'IN_PROGRESS'],
                target_date__lt=timezone.now().date()
            )
        if filter_form.cleaned_data.get('search'):
            search = filter_form.cleaned_data['search']
            findings = findings.filter(finding_number__icontains=search)
    
    findings = findings.select_related(
        'inspection', 'assigned_to', 'assigned_by'
    ).order_by('-created_at')
    
    context = {
        'findings': findings,
        'filter_form': filter_form,
    }
    
    return render(request, 'inspections/findings_list.html', context)


@login_required
def finding_detail(request, pk):
    """View finding details and update action"""
    
    finding = get_object_or_404(
        InspectionFinding.objects.select_related(
            'inspection', 'assigned_to', 'assigned_by', 'closed_by'
        ),
        pk=pk
    )
    
    # Check permission
    if not (request.user.is_superuser or 
            finding.inspection.plant == request.user.plant or
            finding.assigned_to == request.user):
        messages.error(request, 'You do not have permission to view this finding.')
        return redirect('inspections:findings_list')
    
    # Handle action update (for assigned person)
    if request.method == 'POST' and finding.assigned_to == request.user:
        action_form = FindingActionForm(request.POST, request.FILES, instance=finding)
        if action_form.is_valid():
            finding = action_form.save(commit=False)
            finding.status = 'UNDER_REVIEW'
            finding.save()
            
            messages.success(request, 'Action updated successfully. Finding sent for review.')
            return redirect('inspections:finding_detail', pk=finding.id)
    else:
        action_form = FindingActionForm(instance=finding)
    
    context = {
        'finding': finding,
        'action_form': action_form,
    }
    
    return render(request, 'inspections/finding_detail.html', context)


@login_required
def finding_assign(request, pk):
    """Assign finding to responsible person (Safety Officer only)"""
    
    # Check permission
    if not (request.user.is_superuser or request.user.role in ['ADMIN', 'SAFETY_MANAGER']):
        messages.error(request, 'You do not have permission to assign findings.')
        return redirect('inspections:findings_list')
    
    finding = get_object_or_404(InspectionFinding, pk=pk)
    
    if request.method == 'POST':
        form = FindingAssignmentForm(request.POST, instance=finding, user=request.user)
        if form.is_valid():
            finding = form.save(commit=False)
            finding.assigned_by = request.user
            finding.status = 'IN_PROGRESS'
            finding.save()
            
            messages.success(
                request,
                f'Finding assigned to {finding.assigned_to.get_full_name()} successfully.'
            )
            return redirect('inspections:finding_detail', pk=finding.id)
    else:
        form = FindingAssignmentForm(instance=finding, user=request.user)
    
    context = {
        'finding': finding,
        'form': form,
    }
    
    return render(request, 'inspections/finding_assign.html', context)


@login_required
def finding_close(request, pk):
    """Close finding (Safety Officer only)"""
    
    # Check permission
    if not (request.user.is_superuser or request.user.role in ['ADMIN', 'SAFETY_MANAGER']):
        messages.error(request, 'You do not have permission to close findings.')
        return redirect('inspections:findings_list')
    
    finding = get_object_or_404(InspectionFinding, pk=pk)
    
    if request.method == 'POST':
        form = FindingClosureForm(request.POST, instance=finding)
        if form.is_valid():
            finding = form.save(commit=False)
            finding.status = 'CLOSED'
            finding.closure_date = timezone.now().date()
            finding.closed_by = request.user
            finding.save()
            
            messages.success(request, 'Finding closed successfully.')
            return redirect('inspections:finding_detail', pk=finding.id)
    else:
        form = FindingClosureForm(instance=finding)
    
    context = {
        'finding': finding,
        'form': form,
    }
    
    return render(request, 'inspections/finding_close.html', context)


# ========================================
# TEMPLATE MANAGEMENT VIEWS (Admin)
# ========================================

@login_required
def template_list(request):
    """List all inspection templates"""
    
    if not (request.user.is_superuser or request.user.role == 'ADMIN'):
        messages.error(request, 'You do not have permission to manage templates.')
        return redirect('inspections:dashboard')
    
    templates = InspectionTemplate.objects.prefetch_related(
        'categories',
        'categories__inspection_points'
    ).order_by('template_name')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'inspections/template_list.html', context)


@login_required
def template_detail(request, pk):
    """View template details with categories and points"""
    
    template = get_object_or_404(InspectionTemplate, pk=pk)
    
    categories = template.categories.prefetch_related(
        'inspection_points'
    ).order_by('sequence_order')
    
    context = {
        'template': template,
        'categories': categories,
    }
    
    return render(request, 'inspections/template_detail.html', context)