from django.urls import path
from . import views

urlpatterns = [path("", views.home), path("api/status", views.status), path("api/upload", views.upload),
               path("api/index", views.index), path("api/ask", views.ask), path("api/notes", views.notes)]
