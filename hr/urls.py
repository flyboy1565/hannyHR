from django.urls import path

from . import views

app_name = 'hr'

urlpatterns = [
    path('', views.HRDashboardView.as_view(), name='dashboard'),

    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/add/', views.EmployeeCreateView.as_view(), name='employee_add'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),

    path('leave-types/', views.LeaveTypeListView.as_view(), name='leavetype_list'),
    path('leave-types/add/', views.LeaveTypeCreateView.as_view(), name='leavetype_add'),
    path('leave-types/<int:pk>/edit/', views.LeaveTypeUpdateView.as_view(), name='leavetype_edit'),
    path('leave-types/<int:pk>/', views.LeaveTypeDetailView.as_view(), name='leavetype_detail'),

    path(
        'leave-types/<int:leave_type_pk>/attributes/add/',
        views.attribute_create,
        name='attribute_add',
    ),
    path(
        'leave-types/<int:leave_type_pk>/attributes/<int:attribute_pk>/edit/',
        views.attribute_edit,
        name='attribute_edit',
    ),
    path(
        'leave-types/<int:leave_type_pk>/attributes/<int:attribute_pk>/delete/',
        views.attribute_delete,
        name='attribute_delete',
    ),

    path('login/', views.HRLoginView.as_view(), name='login'),
    path('logout/', views.HRLogoutView.as_view(), name='logout'),
]