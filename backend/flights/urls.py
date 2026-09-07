from django.urls import path

from . import views

urlpatterns = [
    path("dashboard", views.dashboard, name="dashboard"),
    path("scan", views.scan, name="scan"),
    path("history", views.history, name="history"),
    path("quick-search", views.quick_search_view, name="quick-search"),
]
