from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('report/', views.scrap_report, name='index'),
    path("coils/", views.coil_list, name="coil_list"),
    path("coils/create/", views.coil_create, name="coil_create"),
    path("coils/<int:pk>/edit/", views.coil_edit, name="coil_edit"),
    path(
        "actual-scrap/",
        views.actual_scrap_list,
        name="actual_scrap_list"
    ),

    path(
        "actual-scrap/create/",
        views.actual_scrap_create,
        name="actual_scrap_create"
    ),

    path(
        "actual-scrap/<int:pk>/edit/",
        views.actual_scrap_edit,
        name="actual_scrap_edit"
    ),
path(
    "production/",
    views.production_department_list,
    name="production_department_list"
),
path(
    "production/<int:department_id>/",
    views.production_entry_list,
    name="production_entry_list"
),
path(
    "production/<int:department_id>/create/",
    views.production_entry_create,
    name="production_entry_create"
),

path(
    "production/entry/<int:pk>/edit/",
    views.production_entry_edit,
    name="production_entry_edit"
),

path(
    "received-scrap/",
    views.received_scrap_list,
    name="received_scrap_list"
),

path(
    "received-scrap/create/",
    views.received_scrap_create,
    name="received_scrap_create"
),

path(
    "received-scrap/<int:pk>/edit/",
    views.received_scrap_edit,
    name="received_scrap_edit"
),
path(
    "monthly-scrap/",
    views.monthly_scrap_report,
    name="monthly_scrap_report"
),
]