from django.urls import path

from .views import (
    assignment_process_view,
    assignment_view,
    download,
    health,
    index,
    process_view,
    progress_view,
)

app_name = 'sorter'

urlpatterns = [
    path('', index, name='index'),
    path('process/', process_view, name='process'),
    path('progress/<str:task_id>/', progress_view, name='progress'),
    path('download/<str:token>/', download, name='download'),
    path('assignment/', assignment_view, name='assignment'),
    path('assignment/process/', assignment_process_view, name='assignment_process'),
    path('health/', health, name='health'),
]
