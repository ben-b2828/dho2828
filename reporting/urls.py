from django.urls import path

from . import views

app_name = "reporting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("export/", views.export_csv, name="export"),
    path("upload/", views.upload, name="upload"),
    path("upload/template/<str:dataset>/", views.download_template, name="template"),
]
