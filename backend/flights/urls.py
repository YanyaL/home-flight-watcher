from django.urls import path

from . import views

urlpatterns = [
    path("dashboard", views.dashboard, name="dashboard"),
    path("scan", views.scan, name="scan"),
    path("scan/<int:job_id>", views.scan_job_detail, name="scan-job-detail"),
    path("scan/<int:job_id>/cancel", views.scan_job_cancel, name="scan-job-cancel"),
    path("scan/<int:job_id>/retry", views.scan_job_retry, name="scan-job-retry"),
    path("history", views.history, name="history"),
    path("quick-search", views.quick_search_view, name="quick-search"),
    path("fx-rates", views.fx_rates, name="fx-rates"),
    path("fx-convert", views.fx_convert, name="fx-convert"),
]
