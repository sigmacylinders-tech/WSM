from calendar import monthrange
from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from Scrap.models import SKU
from .models import ActualWaste, Department, ReceivedWaste, ReceivedWasteUnit, WasteUnits, ActualWasteUnit
from .forms import ActualWasteForm, ReceivedWasteForm, ActualWasteUnitFormSet, ReceivedWasteUnitFormSet


def actual_waste_list(request):
    selected_date = request.GET.get(
        "date",
        timezone.localdate().isoformat()
    )

    entries = (
        ActualWaste.objects
        .select_related("department")
        .prefetch_related("unit_lines__sku", "unit_lines__units")
        .filter(date=selected_date)
        .order_by("department__name")
    )

    return render(
        request,
        "waste/actual_waste_list.html",
        {
            "entries": entries,
            "selected_date": selected_date,
        },
    )


def actual_waste_create(request):
    if request.method == "POST":
        form = ActualWasteForm(request.POST)
        formset = ActualWasteUnitFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            waste = form.save()
            formset.instance = waste
            formset.save()
            return redirect("actual_waste_list")
    else:
        form = ActualWasteForm()
        formset = ActualWasteUnitFormSet()

    return render(
        request,
        "waste/actual_waste_form.html",
        {"form": form, "formset": formset, "title": "Add Actual Waste"},
    )


def actual_waste_edit(request, pk):
    entry = get_object_or_404(ActualWaste, pk=pk)

    if request.method == "POST":
        form = ActualWasteForm(request.POST, instance=entry)
        formset = ActualWasteUnitFormSet(request.POST, instance=entry)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("actual_waste_list")
    else:
        form = ActualWasteForm(instance=entry)
        formset = ActualWasteUnitFormSet(instance=entry)

    return render(
        request,
        "waste/actual_waste_form.html",
        {"form": form, "formset": formset, "title": "Edit Actual Waste"},
    )


def received_waste_list(request):
    selected_date = request.GET.get(
        "date",
        timezone.localdate().isoformat()
    )

    entries = (
        ReceivedWaste.objects
        .select_related("department")
        .prefetch_related("unit_lines__sku", "unit_lines__units")
        .filter(date=selected_date)
        .order_by("department__name")
    )

    return render(
        request,
        "waste/received_waste_list.html",
        {
            "entries": entries,
            "selected_date": selected_date,
        },
    )


def received_waste_create(request):
    if request.method == "POST":
        form = ReceivedWasteForm(request.POST)
        formset = ReceivedWasteUnitFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            waste = form.save()
            formset.instance = waste
            formset.save()
            return redirect("received_waste_list")

    else:
        form = ReceivedWasteForm()
        formset = ReceivedWasteUnitFormSet()

    return render(
        request,
        "waste/received_waste_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Add Received Waste",
        },
    )


def received_waste_edit(request, pk):
    entry = get_object_or_404(
        ReceivedWaste,
        pk=pk,
    )

    if request.method == "POST":
        form = ReceivedWasteForm(
            request.POST,
            instance=entry,
        )
        formset = ReceivedWasteUnitFormSet(
            request.POST,
            instance=entry,
        )

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("received_waste_list")

    else:
        form = ReceivedWasteForm(instance=entry)
        formset = ReceivedWasteUnitFormSet(instance=entry)

    return render(
        request,
        "waste/received_waste_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Edit Received Waste",
        },
    )


@staff_member_required
def waste_report(request):

    selected_month = request.GET.get(
        "month",
        timezone.localdate().strftime("%Y-%m")
    )

    selected_department = request.GET.get(
        "department",
        ""
    )


    year, month = map(
        int,
        selected_month.split("-")
    )


    start_date = datetime(
        year,
        month,
        1
    ).date()


    end_date = datetime(
        year,
        month,
        monthrange(year, month)[1]
    ).date()


    departments = Department.objects.all()
    department_lookup = {
        dept.pk: dept
        for dept in departments
    }


    # =========================
    # Base querysets (headers)
    # =========================

    received_qs = ReceivedWaste.objects.filter(
        date__range=(start_date, end_date)
    )

    actual_qs = ActualWaste.objects.filter(
        date__range=(start_date, end_date)
    )


    if selected_department:

        received_qs = received_qs.filter(
            department_id=selected_department
        )

        actual_qs = actual_qs.filter(
            department_id=selected_department
        )


    # =========================
    # Weight totals per department
    # (basket-level weight — cannot be split by SKU/unit)
    # =========================

    received_weight_totals = (
        received_qs
        .values("department_id")
        .annotate(total_kg=Sum("waste_kg"))
    )

    actual_weight_totals = (
        actual_qs
        .values("department_id")
        .annotate(total_kg=Sum("waste_kg"))
    )


    weight_report_data = {}


    for row in received_weight_totals:

        dept_id = row["department_id"]

        weight_report_data.setdefault(
            dept_id,
            {
                "department": department_lookup.get(dept_id),
                "received_kg": 0,
                "recorded_kg": 0,
            },
        )

        weight_report_data[dept_id]["received_kg"] += row["total_kg"] or 0


    for row in actual_weight_totals:

        dept_id = row["department_id"]

        weight_report_data.setdefault(
            dept_id,
            {
                "department": department_lookup.get(dept_id),
                "received_kg": 0,
                "recorded_kg": 0,
            },
        )

        weight_report_data[dept_id]["recorded_kg"] += row["total_kg"] or 0


    weight_report = []

    for row in weight_report_data.values():

        row["variance"] = (
            row["recorded_kg"]
            -
            row["received_kg"]
        )

        weight_report.append(row)


    weight_report.sort(
        key=lambda r: r["department"].name
    )


    # =========================
    # Unit counts per department + SKU + unit type
    # (line-level quantities — no weight available here)
    # =========================

    received_unit_totals = (
        ReceivedWasteUnit.objects
        .filter(
            waste__date__range=(start_date, end_date)
        )
        .filter(
            waste__department_id=selected_department
        ) if selected_department else ReceivedWasteUnit.objects.filter(
            waste__date__range=(start_date, end_date)
        )
    )

    received_unit_totals = (
        received_unit_totals
        .values("waste__department_id", "sku_id", "units_id")
        .annotate(total_units=Sum("nb_of_units"))
    )


    actual_unit_totals = (
        ActualWasteUnit.objects
        .filter(
            waste__date__range=(start_date, end_date)
        )
        .filter(
            waste__department_id=selected_department
        ) if selected_department else ActualWasteUnit.objects.filter(
            waste__date__range=(start_date, end_date)
        )
    )

    actual_unit_totals = (
        actual_unit_totals
        .values("waste__department_id", "sku_id", "units_id")
        .annotate(total_units=Sum("nb_of_units"))
    )


    sku_lookup = {
        sku.pk: sku
        for sku in SKU.objects.all()
    }

    unit_lookup = {
        unit.pk: unit
        for unit in WasteUnits.objects.all()
    }


    units_report_data = {}


    for row in received_unit_totals:

        key = (
            row["waste__department_id"],
            row["sku_id"],
            row["units_id"],
        )

        units_report_data.setdefault(
            key,
            {
                "department": department_lookup.get(row["waste__department_id"]),
                "sku": sku_lookup.get(row["sku_id"]),
                "units": unit_lookup.get(row["units_id"]),

                "received_nb_units": 0,
                "recorded_nb_units": 0,
            },
        )

        units_report_data[key]["received_nb_units"] += row["total_units"] or 0


    for row in actual_unit_totals:

        key = (
            row["waste__department_id"],
            row["sku_id"],
            row["units_id"],
        )

        units_report_data.setdefault(
            key,
            {
                "department": department_lookup.get(row["waste__department_id"]),
                "sku": sku_lookup.get(row["sku_id"]),
                "units": unit_lookup.get(row["units_id"]),

                "received_nb_units": 0,
                "recorded_nb_units": 0,
            },
        )

        units_report_data[key]["recorded_nb_units"] += row["total_units"] or 0


    units_report = []

    for row in units_report_data.values():

        row["variance"] = (
            row["recorded_nb_units"]
            -
            row["received_nb_units"]
        )

        units_report.append(row)


    units_report.sort(
        key=lambda r: (
            r["department"].name if r["department"] else "",
            r["sku"].name if r["sku"] else "",
            r["units"].name if r["units"] else "",
        )
    )


    return render(
        request,
        "waste/waste_report.html",
        {
            "weight_report": weight_report,
            "units_report": units_report,
            "departments": departments,
            "selected_month": selected_month,
            "selected_department": selected_department,
        }
    )