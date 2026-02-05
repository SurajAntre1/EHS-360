from django.urls import path,reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('forget-password/',views.ForgetPasswordView.as_view(), name='forget-password'),
    path('reset-password/',auth_views.PasswordResetView.as_view(),name='password_reset'),
    path('reset-password/done/',auth_views.PasswordResetDoneView.as_view(),name='password_reset_done'),
    path('reset-password-confirm/<uidb64>/<token>/',auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html',success_url=reverse_lazy('accounts:password_reset_complete')),
        name='password_reset_confirm'),
    path('reset-password-complete/',auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete'),

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
    # path('permissions-only/', views.UserPermissionsOnlyView.as_view(), name='permissions_only'),
    # path('permissions-only/<int:user_id>/update/', views.update_user_permission, name='update_permission'),
    # path('permissions-only/bulk-update/', views.bulk_update_permissions, name='bulk_update_permissions'),
    
    # # Quick Actions
    # path('permissions/<int:user_id>/grant/<str:permission_type>/', views.quick_grant_permission, name='grant_permission'),
    # path('permissions/<int:user_id>/revoke/<str:permission_type>/', views.quick_revoke_permission, name='revoke_permission'),
    
    # Bulk Actions
    # path('permissions/bulk-grant/', views.bulk_grant_permissions, name='bulk_grant_permissions'),
     # Hierarchical permission management
    path('role/<int:role_id>/permissions-hierarchical/', 
         views.RolePermissionsHierarchicalView.as_view(), 
         name='role_permissions_hierarchical'),
    
    path('toggle-module-access/<int:role_id>/', 
         views.toggle_module_access, 
         name='toggle_module_access'),
    
    path('toggle-permission-in-module/<int:role_id>/', 
         views.toggle_permission_in_module, 
         name='toggle_permission_in_module'),
    
    #roles and permission
    path('role-list/',views.RolePermission.as_view(), name='role-list'),
    path('createrole/', views.RoleCreateView.as_view(), name='createrole'),
    path('updaterole/<int:role_id>', views.RoleUpdateView.as_view(), name='updaterole'),
]