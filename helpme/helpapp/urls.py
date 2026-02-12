from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('ask/', views.ask, name='ask'),
    path('files/', views.file_portal, name='file_portal'),
    path('files/session/clear/', views.clear_file_session, name='clear_file_session'),
    path('files/all/', views.all_files, name='all_files'),
    path('files/delete/<int:doc_collection_id>/', views.delete_file, name='delete_file'),
]
