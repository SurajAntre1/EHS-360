# apps/data_collection/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from .models import (
    DataCollectionPeriod,
    MonthlyDataCollection,
    DataCollectionResponse,
    DataCollectionQuestion,
    DataCollectionCategory,
    DataCollectionAttachment,
    DataCollectionComment
)
from .forms import (
    MonthlyDataCollectionForm,
    DynamicDataCollectionForm,
    DataCollectionAttachmentForm,
    DataCollectionCommentForm,
    DataCollectionReviewForm
)
from apps.organizations.models import Department
import json


@login_required
def data_collection_dashboard(request):
    """Dashboard showing data collection overview"""
    
    # Get active periods
    active_periods = DataCollectionPeriod.objects.filter(
        status='ACTIVE'
    ).order_by('-year', '-month')[:5]
    
    # Get user's collections
    user_collections = MonthlyDataCollection.objects.filter(
        reported_by=request.user
    ).select_related('period', 'plant', 'location').order_by('-created_at')[:10]
    
    # Get pending collections (assigned but not completed)
    pending_collections = MonthlyDataCollection.objects.filter(
        reported_by=request.user,
        status='DRAFT'
    ).count()
    
    # Get collections pending approval (if user has approval rights)
    pending_approvals = MonthlyDataCollection.objects.filter(
        status__in=['SUBMITTED', 'UNDER_REVIEW']
    ).count()
    
    # Statistics
    total_submitted = MonthlyDataCollection.objects.filter(
        reported_by=request.user,
        status='SUBMITTED'
    ).count()
    
    total_approved = MonthlyDataCollection.objects.filter(
        reported_by=request.user,
        status='APPROVED'
    ).count()
    
    context = {
        'active_periods': active_periods,
        'user_collections': user_collections,
        'pending_collections': pending_collections,
        'pending_approvals': pending_approvals,
        'total_submitted': total_submitted,
        'total_approved': total_approved,
    }
    
    return render(request, 'data_collection/collection_dashboard.html', context)


@login_required
def data_collection_list(request):
    """List all data collections with filters"""
    
    collections = MonthlyDataCollection.objects.select_related(
        'period', 'plant', 'location', 'reported_by'
    ).order_by('-period__year', '-period__month', 'plant', 'location')
    
    # Apply filters
    period_id = request.GET.get('period')
    status = request.GET.get('status')
    plant_id = request.GET.get('plant')
    
    if period_id:
        collections = collections.filter(period_id=period_id)
    
    if status:
        collections = collections.filter(status=status)
    
    if plant_id:
        collections = collections.filter(plant_id=plant_id)
    
    # If not admin/manager, show only user's collections
    if not request.user.is_staff:
        collections = collections.filter(reported_by=request.user)
    
    # Pagination
    paginator = Paginator(collections, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    periods = DataCollectionPeriod.objects.all().order_by('-year', '-month')
    
    context = {
        'page_obj': page_obj,
        'periods': periods,
        'selected_period': period_id,
        'selected_status': status,
        'selected_plant': plant_id,
    }
    
    return render(request, 'data_collection/data_collection_list.html', context)


@login_required
def create_data_collection(request, period_id):
    """Create new data collection for a period"""
    
    period = get_object_or_404(DataCollectionPeriod, id=period_id)
    
    if period.status != 'ACTIVE':
        messages.error(request, 'This period is not active for data collection.')
        return redirect('data_collection:dashboard')
    
    # Check if collection already exists for user's location
    if hasattr(request.user, 'location') and request.user.location:
        existing = MonthlyDataCollection.objects.filter(
            period=period,
            plant=request.user.plant,
            location=request.user.location
        ).first()
        
        if existing:
            messages.info(request, 'Data collection already exists. Redirecting to edit.')
            return redirect('data_collection:edit_collection', pk=existing.id)
    
    if request.method == 'POST':
        form = MonthlyDataCollectionForm(request.POST, user=request.user)
        dynamic_form = DynamicDataCollectionForm(
            request.POST,
            request.FILES,
            plant=request.user.plant if hasattr(request.user, 'plant') else None
        )
        
        if form.is_valid() and dynamic_form.is_valid():
            try:
                with transaction.atomic():
                    # Create collection
                    collection = form.save(commit=False)
                    collection.period = period
                    collection.reported_by = request.user
                    collection.save()
                    
                    # Save responses
                    save_responses(collection, dynamic_form)
                    
                    messages.success(request, 'Data collection created successfully.')
                    return redirect('data_collection:edit_collection', pk=collection.id)
            
            except Exception as e:
                messages.error(request, f'Error creating collection: {str(e)}')
    else:
        form = MonthlyDataCollectionForm(user=request.user)
        dynamic_form = DynamicDataCollectionForm(
            plant=request.user.plant if hasattr(request.user, 'plant') else None
        )
    
    # Get departments for form
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'form': form,
        'dynamic_form': dynamic_form,
        'period': period,
        'departments': departments,
        'categories_with_questions': dynamic_form.get_questions_by_category(),
    }
    
    return render(request, 'data_collection/create_collection.html', context)


@login_required
def edit_data_collection(request, pk):
    """Edit existing data collection"""
    
    collection = get_object_or_404(MonthlyDataCollection, id=pk)
    
    # Check permissions
    if not request.user.is_staff and collection.reported_by != request.user:
        messages.error(request, 'You do not have permission to edit this collection.')
        return redirect('data_collection:dashboard')
    
    # Check if collection can be edited
    if collection.status not in ['DRAFT', 'REJECTED']:
        messages.warning(request, 'This collection cannot be edited in its current status.')
        return redirect('data_collection:view_collection', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_draft':
            form = MonthlyDataCollectionForm(request.POST, instance=collection)
            dynamic_form = DynamicDataCollectionForm(
                request.POST,
                request.FILES,
                plant=collection.plant,
                collection=collection
            )
            
            if form.is_valid() and dynamic_form.is_valid():
                try:
                    with transaction.atomic():
                        form.save()
                        save_responses(collection, dynamic_form)
                        
                        messages.success(request, 'Draft saved successfully.')
                        return redirect('data_collection:edit_collection', pk=pk)
                
                except Exception as e:
                    messages.error(request, f'Error saving draft: {str(e)}')
        
        elif action == 'submit':
            form = MonthlyDataCollectionForm(request.POST, instance=collection)
            dynamic_form = DynamicDataCollectionForm(
                request.POST,
                request.FILES,
                plant=collection.plant,
                collection=collection
            )
            
            if form.is_valid() and dynamic_form.is_valid():
                try:
                    with transaction.atomic():
                        form.save()
                        save_responses(collection, dynamic_form)
                        
                        # Submit collection
                        collection.submit(request.user)
                        
                        messages.success(request, 'Data collection submitted successfully.')
                        return redirect('data_collection:view_collection', pk=pk)
                
                except Exception as e:
                    messages.error(request, f'Error submitting collection: {str(e)}')
    else:
        form = MonthlyDataCollectionForm(instance=collection)
        dynamic_form = DynamicDataCollectionForm(
            plant=collection.plant,
            collection=collection
        )
    
    # Get departments
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'form': form,
        'dynamic_form': dynamic_form,
        'collection': collection,
        'departments': departments,
        'categories_with_questions': dynamic_form.get_questions_by_category(),
    }
    
    return render(request, 'data_collection/edit_collection.html', context)


@login_required
def view_data_collection(request, pk):
    """View data collection details"""
    
    collection = get_object_or_404(
        MonthlyDataCollection.objects.select_related(
            'period', 'plant', 'zone', 'location', 'sublocation',
            'department', 'reported_by', 'submitted_by', 'approved_by'
        ).prefetch_related(
            'responses__question__category',
            'attachments',
            'comments__commented_by'
        ),
        id=pk
    )
    
    # Check permissions
    if not request.user.is_staff and collection.reported_by != request.user:
        messages.error(request, 'You do not have permission to view this collection.')
        return redirect('data_collection:dashboard')
    
    # Group responses by category
    categories = DataCollectionCategory.objects.filter(
        is_active=True
    ).prefetch_related(
        Prefetch(
            'questions__responses',
            queryset=DataCollectionResponse.objects.filter(collection=collection)
        )
    ).order_by('display_order')
    
    # Comment form
    comment_form = DataCollectionCommentForm()
    
    # Review form (for approvers)
    review_form = DataCollectionReviewForm() if request.user.is_staff else None
    
    context = {
        'collection': collection,
        'categories': categories,
        'comment_form': comment_form,
        'review_form': review_form,
    }
    
    return render(request, 'data_collection/view_collection.html', context)


@login_required
def add_comment(request, pk):
    """Add comment to data collection"""
    
    collection = get_object_or_404(MonthlyDataCollection, id=pk)
    
    if request.method == 'POST':
        form = DataCollectionCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.collection = collection
            comment.commented_by = request.user
            comment.save()
            
            messages.success(request, 'Comment added successfully.')
        else:
            messages.error(request, 'Error adding comment.')
    
    return redirect('data_collection:view_collection', pk=pk)


@login_required
def review_collection(request, pk):
    """Review/Approve/Reject data collection"""
    
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to review collections.')
        return redirect('data_collection:dashboard')
    
    collection = get_object_or_404(MonthlyDataCollection, id=pk)
    
    if request.method == 'POST':
        form = DataCollectionReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            comments = form.cleaned_data['comments']
            
            try:
                if action == 'approve':
                    collection.approve(request.user, comments)
                    messages.success(request, 'Collection approved successfully.')
                
                elif action == 'reject':
                    collection.reject(request.user, comments)
                    messages.success(request, 'Collection rejected.')
                
                elif action == 'request_changes':
                    collection.review(request.user, comments)
                    messages.success(request, 'Review comments sent.')
                
                return redirect('data_collection:view_collection', pk=pk)
            
            except Exception as e:
                messages.error(request, f'Error processing review: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    
    return redirect('data_collection:view_collection', pk=pk)


def save_responses(collection, dynamic_form):
    """Helper function to save form responses"""
    
    for field_name, field in dynamic_form.fields.items():
        if field_name.startswith('question_') and hasattr(field, 'question'):
            question = field.question
            value = dynamic_form.cleaned_data.get(field_name)
            
            # Get or create response
            response, created = DataCollectionResponse.objects.get_or_create(
                collection=collection,
                question=question
            )
            
            # Set value based on field type
            if question.field_type == 'NUMBER':
                response.numeric_value = value
                # Get unit
                unit_field_name = f'question_{question.id}_unit'
                if unit_field_name in dynamic_form.cleaned_data:
                    response.unit_used = dynamic_form.cleaned_data[unit_field_name]
            
            elif question.field_type in ['TEXT', 'TEXTAREA', 'EMAIL']:
                response.text_value = value or ''
            
            elif question.field_type == 'DATE':
                response.date_value = value
            
            elif question.field_type == 'CHECKBOX':
                response.boolean_value = value
            
            elif question.field_type in ['DROPDOWN', 'RADIO']:
                response.selected_option = value or ''
            
            elif question.field_type == 'FILE':
                if value:
                    response.file_value = value
            
            # Get remarks
            remarks_field_name = f'question_{question.id}_remarks'
            if remarks_field_name in dynamic_form.cleaned_data:
                response.remarks = dynamic_form.cleaned_data[remarks_field_name] or ''
            
            response.save()


@login_required
def delete_collection(request, pk):
    """Delete data collection (only drafts)"""
    
    collection = get_object_or_404(MonthlyDataCollection, id=pk)
    
    # Check permissions
    if not request.user.is_staff and collection.reported_by != request.user:
        messages.error(request, 'You do not have permission to delete this collection.')
        return redirect('data_collection:dashboard')
    
    # Only allow deletion of drafts
    if collection.status != 'DRAFT':
        messages.error(request, 'Only draft collections can be deleted.')
        return redirect('data_collection:view_collection', pk=pk)
    
    if request.method == 'POST':
        collection.delete()
        messages.success(request, 'Collection deleted successfully.')
        return redirect('data_collection:list')
    
    return render(request, 'data_collection/delete_confirm.html', {'collection': collection})




# Add these CLASS-BASED VIEWS to your apps/data_collection/views.py

from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import (
    DataCollectionQuestion, 
    DataCollectionCategory,
    DataCollectionPeriod,
    MonthlyDataCollection
)
from apps.organizations.models import Plant
import json


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require staff or superuser access"""
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def handle_no_permission(self):
        from django.contrib import messages
        messages.error(self.request, 'You do not have permission to access this page.')
        return super().handle_no_permission()


class QuestionAssignmentView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """
    Main page for managing question assignments to plants
    """
    model = DataCollectionQuestion
    template_name = 'data_collection/question_assignment.html'
    context_object_name = 'questions'
    
    def get_queryset(self):
        queryset = DataCollectionQuestion.objects.filter(
            is_active=True,
            category__is_active=True
        ).select_related('category').prefetch_related('applicable_plants')
        
        # Apply filters
        category = self.request.GET.get('category')
        assignment_type = self.request.GET.get('assignment_type')
        
        if category:
            queryset = queryset.filter(category_id=category)
        
        if assignment_type == 'all_plants':
            queryset = queryset.filter(applicable_to_all_plants=True)
        elif assignment_type == 'specific_plants':
            queryset = queryset.filter(applicable_to_all_plants=False)
        
        return queryset.order_by('category__display_order', 'display_order')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all categories
        context['categories'] = DataCollectionCategory.objects.filter(
            is_active=True
        ).order_by('display_order')
        
        # Get all plants
        context['plants'] = Plant.objects.filter(is_active=True).order_by('name')
        
        # Group questions by category
        questions_by_category = {}
        for question in self.get_queryset():
            if question.category not in questions_by_category:
                questions_by_category[question.category] = []
            questions_by_category[question.category].append(question)
        
        context['questions_by_category'] = questions_by_category
        
        # Statistics
        context['total_questions'] = DataCollectionQuestion.objects.filter(
            is_active=True
        ).count()
        
        context['all_plants_count'] = DataCollectionQuestion.objects.filter(
            is_active=True,
            applicable_to_all_plants=True
        ).count()
        
        context['specific_plants_count'] = DataCollectionQuestion.objects.filter(
            is_active=True,
            applicable_to_all_plants=False
        ).count()
        
        # Filter selections
        context['selected_category'] = self.request.GET.get('category')
        context['selected_type'] = self.request.GET.get('assignment_type')
        
        # Month options
        context['months'] = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        
        return context


class GetQuestionAssignmentView(LoginRequiredMixin, StaffRequiredMixin, View):
    """
    AJAX view to get current assignment details for a question
    """
    
    def get(self, request, question_id):
        question = get_object_or_404(DataCollectionQuestion, id=question_id)
        
        assigned_plants = list(question.applicable_plants.values_list('id', flat=True))
        
        # Parse assigned months if exists
        assigned_months = []
        if hasattr(question, 'applicable_months') and question.applicable_months:
            assigned_months = [
                int(m.strip()) 
                for m in question.applicable_months.split(',') 
                if m.strip()
            ]
        
        data = {
            'applicable_to_all_plants': question.applicable_to_all_plants,
            'assigned_plants': assigned_plants,
            'assigned_months': assigned_months,
        }
        
        return JsonResponse(data)


class UpdateQuestionAssignmentView(LoginRequiredMixin, StaffRequiredMixin, View):
    """
    AJAX view to update question assignment
    """
    
    def post(self, request, question_id):
        try:
            question = get_object_or_404(DataCollectionQuestion, id=question_id)
            
            # Get assignment type
            assignment_type = request.POST.get('assignment_type')
            
            if assignment_type == 'all':
                # Assign to all plants
                question.applicable_to_all_plants = True
                question.save()
                question.applicable_plants.clear()
            
            elif assignment_type == 'specific':
                # Assign to specific plants
                question.applicable_to_all_plants = False
                question.save()
                
                # Get selected plant IDs
                plant_ids = request.POST.getlist('plants[]')
                
                if plant_ids:
                    plants = Plant.objects.filter(id__in=plant_ids)
                    question.applicable_plants.set(plants)
                else:
                    question.applicable_plants.clear()
            
            # Handle month assignment (if field exists)
            if hasattr(question, 'applicable_months'):
                month_values = request.POST.getlist('months[]')
                if month_values:
                    question.applicable_months = ','.join(month_values)
                else:
                    question.applicable_months = ''
                question.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Assignment updated successfully'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


class BulkAssignAllPlantsView(LoginRequiredMixin, StaffRequiredMixin, View):
    """
    AJAX view to bulk assign all questions to all plants
    """
    
    def post(self, request):
        try:
            count = DataCollectionQuestion.objects.filter(
                is_active=True
            ).update(applicable_to_all_plants=True)
            
            # Clear specific plant assignments
            for question in DataCollectionQuestion.objects.filter(is_active=True):
                question.applicable_plants.clear()
            
            return JsonResponse({
                'success': True,
                'count': count,
                'message': f'{count} questions updated'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


class BulkAssignByCategoryView(LoginRequiredMixin, StaffRequiredMixin, View):
    """
    AJAX view to bulk assign all questions in a category to specific plants
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            category_code = data.get('category')
            plant_ids = data.get('plant_ids', [])
            
            if not category_code or not plant_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'Category and plant IDs are required'
                }, status=400)
            
            # Get category
            category = DataCollectionCategory.objects.get(code=category_code.upper())
            
            # Get plants
            plants = Plant.objects.filter(id__in=plant_ids)
            
            if not plants.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'No valid plants found'
                }, status=400)
            
            # Update questions
            questions = DataCollectionQuestion.objects.filter(
                category=category,
                is_active=True
            )
            
            count = 0
            for question in questions:
                question.applicable_to_all_plants = False
                question.save()
                question.applicable_plants.set(plants)
                count += 1
            
            return JsonResponse({
                'success': True,
                'count': count,
                'message': f'{count} questions in {category.name} assigned to {plants.count()} plants'
            })
        
        except DataCollectionCategory.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Category not found'
            }, status=404)
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


class PlantWiseQuestionsView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    """
    View all questions applicable to a specific plant
    """
    model = Plant
    template_name = 'data_collection/plant_wise_questions.html'
    context_object_name = 'plant'
    pk_url_kwarg = 'plant_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plant = self.get_object()
        
        # Get all applicable questions
        questions = DataCollectionQuestion.objects.filter(
            Q(applicable_to_all_plants=True) |
            Q(applicable_plants=plant),
            is_active=True,
            category__is_active=True
        ).distinct().select_related('category').order_by(
            'category__display_order',
            'display_order'
        )
        
        # Group by category
        questions_by_category = {}
        for question in questions:
            if question.category not in questions_by_category:
                questions_by_category[question.category] = []
            questions_by_category[question.category].append(question)
        
        context['questions_by_category'] = questions_by_category
        context['total_questions'] = questions.count()
        
        return context


class MonthWiseQuestionsView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """
    View questions filtered by month
    """
    model = DataCollectionQuestion
    template_name = 'data_collection/month_wise_questions.html'
    context_object_name = 'questions'
    
    def get_queryset(self):
        selected_month = self.request.GET.get('month')
        
        questions = DataCollectionQuestion.objects.filter(
            is_active=True,
            category__is_active=True
        ).select_related('category').order_by(
            'category__display_order',
            'display_order'
        )
        
        if selected_month:
            # Filter by month if field exists
            filtered_questions = []
            for q in questions:
                if hasattr(q, 'applicable_months') and q.applicable_months:
                    months = [int(m.strip()) for m in q.applicable_months.split(',') if m.strip()]
                    if int(selected_month) in months:
                        filtered_questions.append(q)
                else:
                    # No month restriction, include for all months
                    filtered_questions.append(q)
            
            return filtered_questions
        
        return questions
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        questions = self.get_queryset()
        
        # Group by category
        questions_by_category = {}
        for question in questions:
            if question.category not in questions_by_category:
                questions_by_category[question.category] = []
            questions_by_category[question.category].append(question)
        
        context['questions_by_category'] = questions_by_category
        
        # Month options
        context['months'] = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        
        context['selected_month'] = self.request.GET.get('month')
        context['total_questions'] = len(questions) if isinstance(questions, list) else questions.count()
        
        return context


# ============================================
# EXISTING CLASS-BASED VIEWS (Keep these)
# ============================================

class DataCollectionDashboardView(LoginRequiredMixin, ListView):
    """Dashboard showing data collection overview"""
    model = DataCollectionPeriod
    template_name = 'data_collection/dashboard.html'
    context_object_name = 'active_periods'
    
    def get_queryset(self):
        return DataCollectionPeriod.objects.filter(
            status='ACTIVE'
        ).order_by('-year', '-month')[:5]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's collections
        context['user_collections'] = MonthlyDataCollection.objects.filter(
            reported_by=self.request.user
        ).select_related('period', 'plant', 'location').order_by('-created_at')[:10]
        
        # Statistics
        context['pending_collections'] = MonthlyDataCollection.objects.filter(
            reported_by=self.request.user,
            status='DRAFT'
        ).count()
        
        context['pending_approvals'] = MonthlyDataCollection.objects.filter(
            status__in=['SUBMITTED', 'UNDER_REVIEW']
        ).count()
        
        context['total_submitted'] = MonthlyDataCollection.objects.filter(
            reported_by=self.request.user,
            status='SUBMITTED'
        ).count()
        
        context['total_approved'] = MonthlyDataCollection.objects.filter(
            reported_by=self.request.user,
            status='APPROVED'
        ).count()
        
        return context


class DataCollectionListView(LoginRequiredMixin, ListView):
    """List all data collections with filters"""
    model = MonthlyDataCollection
    template_name = 'data_collection/collection_list.html'
    context_object_name = 'page_obj'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = MonthlyDataCollection.objects.select_related(
            'period', 'plant', 'location', 'reported_by'
        ).order_by('-period__year', '-period__month', 'plant', 'location')
        
        # Apply filters
        period_id = self.request.GET.get('period')
        status = self.request.GET.get('status')
        plant_id = self.request.GET.get('plant')
        
        if period_id:
            queryset = queryset.filter(period_id=period_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if plant_id:
            queryset = queryset.filter(plant_id=plant_id)
        
        # If not admin/manager, show only user's collections
        if not self.request.user.is_staff:
            queryset = queryset.filter(reported_by=self.request.user)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        context['periods'] = DataCollectionPeriod.objects.all().order_by('-year', '-month')
        context['selected_period'] = self.request.GET.get('period')
        context['selected_status'] = self.request.GET.get('status')
        context['selected_plant'] = self.request.GET.get('plant')
        
        return context