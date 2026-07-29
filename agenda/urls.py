from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.agenda_diaria, name="diaria"),
    path("excel/", views.agenda_diaria_excel, name="diaria_excel"),
]
