from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # User Management (Admin Only)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<int:pk>/toggle-active/', views.UserToggleActiveView.as_view(), name='user_toggle_active'),



    ####permission page 
    # path('permissions/', views.UserPermissionManagementView.as_view(), name='permission_management'),
    # path('permissions/<int:pk>/edit/', views.UserPermissionUpdateView.as_view(), name='permission_edit'),
    
    # NEW: Separate Permissions-Only Page
    path('permissions-only/', views.UserPermissionsOnlyView.as_view(), name='permissions_only'),
    path('permissions-only/<int:user_id>/update/', views.update_user_permission, name='update_permission'),
    path('permissions-only/bulk-update/', views.bulk_update_permissions, name='bulk_update_permissions'),
    
    # # Quick Actions
    # path('permissions/<int:user_id>/grant/<str:permission_type>/', views.quick_grant_permission, name='grant_permission'),
    # path('permissions/<int:user_id>/revoke/<str:permission_type>/', views.quick_revoke_permission, name='revoke_permission'),
    
    # Bulk Actions
    # path('permissions/bulk-grant/', views.bulk_grant_permissions, name='bulk_grant_permissions'),
    #roles and permission
    path('role-list/',views.RolePermission.as_view(), name='role-list'),
    path('createrole/', views.RoleCreateView.as_view(), name='createrole'),
]