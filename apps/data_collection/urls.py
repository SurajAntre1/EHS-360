# Add these URLs to your apps/data_collection/urls.py

from django.urls import path
from . import views

app_name = 'data_collection'

urlpatterns = [
    # Dashboard
    path('', views.data_collection_dashboard, name='dashboard'),
    
    # Collection CRUD
    path('list/', views.data_collection_list, name='list'),
    path('create/<int:period_id>/', views.create_data_collection, name='create_collection'),
    path('edit/<int:pk>/', views.edit_data_collection, name='edit_collection'),
    path('view/<int:pk>/', views.view_data_collection, name='view_collection'),
    path('delete/<int:pk>/', views.delete_collection, name='delete_collection'),
    
    # Comments & Review
    path('add-comment/<int:pk>/', views.add_comment, name='add_comment'),
    path('review/<int:pk>/', views.review_collection, name='review_collection'),
    
    # Question Assignment Management
    path('question-assignment/', 
         views.QuestionAssignmentView.as_view(), 
         name='question_assignment'),
    
    # AJAX endpoints for question assignment
    path('get-question-assignment/<int:question_id>/', 
         views.GetQuestionAssignmentView.as_view(), 
         name='get_question_assignment'),

    path('update-question-assignment/<int:question_id>/', 
         views.UpdateQuestionAssignmentView.as_view(), 
         name='update_question_assignment'),
    
    # Bulk operations
    path('bulk-assign-all-plants/', 
         views.BulkAssignAllPlantsView.as_view(), 
         name='bulk_assign_all_plants'),
    
    path('bulk-assign-by-category/', 
         views.BulkAssignByCategoryView.as_view(), 
         name='bulk_assign_by_category'),
    
    # Plant-wise and Month-wise views
    path('plant-wise-questions/<int:plant_id>/', 
         views.PlantWiseQuestionsView.as_view(), 
         name='plant_wise_questions'),
    
    path('month-wise-questions/', 
         views.MonthWiseQuestionsView.as_view(), 
         name='month_wise_questions'),
]