"""
URL patterns for the docs app.
"""

from django.urls import path
from . import views

app_name = 'docs'

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('page/<int:page_id>/', views.page_detail, name='page_detail'),
    path('section/<int:section_id>/', views.section_detail, name='section_detail'),
    path('api/audio/', views.get_audio, name='get_audio'),
]
