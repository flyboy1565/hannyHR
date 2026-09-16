from django.urls import path

from . import views

app_name = 'leave'

urlpatterns = [
    path('', views.LeaveTypeListView.as_view(), name='leave_type_list'),
    path('requests/', views.LeaveRequestListView.as_view(), name='request_list'),
    path('new/', views.LeaveRequestCreateView.as_view(), name='request_new'),
    path('<int:pk>/edit/', views.LeaveRequestEditView.as_view(), name='request_edit'),
    path('<int:pk>/', views.LeaveRequestDetailView.as_view(), name='leave_detail'),
]