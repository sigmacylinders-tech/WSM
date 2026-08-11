from django.urls import path
from . import views

urlpatterns = [
path(
    "actual-waste/",
    views.actual_waste_list,
    name="actual_waste_list",
),

path(
    "actual-waste/create/",
    views.actual_waste_create,
    name="actual_waste_create",
),

path(
    "actual-waste/<int:pk>/edit/",
    views.actual_waste_edit,
    name="actual_waste_edit",
),
path(
    "received-waste/",
    views.received_waste_list,
    name="received_waste_list",
),

path(
    "received-waste/create/",
    views.received_waste_create,
    name="received_waste_create",
),

path(
    "received-waste/<int:pk>/edit/",
    views.received_waste_edit,
    name="received_waste_edit",
),
path(
    "waste-report/",
    views.waste_report,
    name="waste_report",
),
]