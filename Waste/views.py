import re
from calendar import monthrange
from collections import defaultdict
from datetime import datetime, date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.http import urlencode

from Scrap.models import SKU
from .models import ActualWaste, Department, ReceivedWaste, ReceivedWasteUnit, WasteUnits, ActualWasteUnit, Project
from .forms import ActualWasteForm, ReceivedWasteForm, ActualWasteUnitFormSet, ReceivedWasteUnitFormSet


def actual_waste_list(request):
    selected_date = request.GET.get(
        "date",
        timezone.localdate().isoformat()
    )

    entries = (
        ActualWaste.objects
        .select_related("department")
        .prefetch_related(
            "unit_lines__sku",
            "unit_lines__units",
            "unit_lines__project",
        )
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

        department = None
        department_id = request.POST.get("department")
        if department_id:
            department = Department.objects.filter(pk=department_id).first()

        formset = ActualWasteUnitFormSet(request.POST, department=department)

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

        department = entry.department
        department_id = request.POST.get("department")
        if department_id:
            department = Department.objects.filter(pk=department_id).first() or entry.department

        formset = ActualWasteUnitFormSet(
            request.POST, instance=entry, department=department
        )

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("actual_waste_list")
    else:
        form = ActualWasteForm(instance=entry)
        formset = ActualWasteUnitFormSet(instance=entry, department=entry.department)

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
        .prefetch_related(
            "unit_lines__sku",
            "unit_lines__units",
            "unit_lines__project",
        )
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

        department = None
        department_id = request.POST.get("department")
        if department_id:
            department = Department.objects.filter(pk=department_id).first()

        formset = ReceivedWasteUnitFormSet(request.POST, department=department)

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
    entry = get_object_or_404(ReceivedWaste, pk=pk)

    if request.method == "POST":
        form = ReceivedWasteForm(request.POST, instance=entry)

        department = entry.department
        department_id = request.POST.get("department")
        if department_id:
            department = Department.objects.filter(pk=department_id).first() or entry.department

        formset = ReceivedWasteUnitFormSet(
            request.POST, instance=entry, department=department
        )

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("received_waste_list")

    else:
        form = ReceivedWasteForm(instance=entry)
        formset = ReceivedWasteUnitFormSet(instance=entry, department=entry.department)

    return render(
        request,
        "waste/received_waste_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Edit Received Waste",
        },
    )

def skus_for_department(request, department_id):
    department = get_object_or_404(Department, pk=department_id)
    skus = department.skus.order_by("name").values("id", "name")
    return JsonResponse(list(skus), safe=False)

# =========================
# Helpers
# =========================

# Serials may be separated by new lines, commas or semicolons
SERIAL_SEPARATORS = re.compile(r"[\n,;]+")

UNIT_GROUP_FIELDS = {
    "department_name": F("waste__department__name"),
    "sku_name": F("sku__name"),
    "unit_name": F("units__name"),
    "project_name": F("project__name"),
}

SERIAL_CONTEXT_FIELDS = {
    **UNIT_GROUP_FIELDS,
    "entry_date": F("waste__date"),
}


def parse_date(value):
    """'YYYY-MM-DD' -> date. Returns None for empty or invalid input."""
    try:
        return date.fromisoformat((value or "").strip())
    except (TypeError, ValueError):
        return None


def month_bounds(year, month):
    """First and last day of a month."""
    return (
        date(year, month, 1),
        date(year, month, monthrange(year, month)[1]),
    )


def resolve_period(request):
    """
    Works out the reporting period from the query string.

    Priority:
        1. ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD (either side may be missing)
        2. ?month=YYYY-MM (kept so old links and bookmarks still work)
        3. Current month
    """
    today = timezone.localdate()

    date_from = parse_date(request.GET.get("date_from"))
    date_to = parse_date(request.GET.get("date_to"))

    if date_from or date_to:
        if date_from and not date_to:
            date_to = today if date_from <= today else date_from
        elif date_to and not date_from:
            date_from = date_to.replace(day=1)

        if date_from > date_to:
            date_from, date_to = date_to, date_from

        return date_from, date_to

    month = request.GET.get("month")

    if month:
        try:
            year, month_number = map(int, month.split("-"))
            return month_bounds(year, month_number)
        except (AttributeError, TypeError, ValueError):
            pass

    return month_bounds(today.year, today.month)


def build_presets(date_from, date_to, extra_params):
    """Quick-select date ranges. extra_params keeps the other filters."""
    today = timezone.localdate()

    this_month_start, this_month_end = month_bounds(today.year, today.month)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    ranges = [
        ("Today", today, today),
        ("Last 7 days", today - timedelta(days=6), today),
        ("Last 30 days", today - timedelta(days=29), today),
        ("This month", this_month_start, this_month_end),
        ("Last month", last_month_start, last_month_end),
        ("Year to date", date(today.year, 1, 1), today),
    ]

    presets = []

    for label, start, end in ranges:
        params = {
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            **{key: value for key, value in extra_params.items() if value},
        }

        presets.append({
            "label": label,
            "query": urlencode(params),
            "active": start == date_from and end == date_to,
        })

    return presets


def parse_id(value):
    """Returns an int id, or None for empty or invalid input."""
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def parse_serials(text):
    """Splits a serial-number text field into a normalized set of serials."""
    serials = set()
    for part in SERIAL_SEPARATORS.split(text or ""):
        serial = "".join(part.split()).upper()  # drop all spaces, ignore case
        if serial:
            serials.add(serial)
    return serials


def variance_pct(recorded, received):
    if not received:
        return None
    return round((recorded - received) * 100 / received, 1)


def build_comparison(received_rows, recorded_rows, key_fields):
    """
    Merges received and recorded totals on key_fields.
    Each input row must contain the key fields plus "total".
    """
    data = {}

    for side, rows in (("received", received_rows), ("recorded", recorded_rows)):
        for row in rows:
            key = tuple(row[field] for field in key_fields)

            entry = data.setdefault(
                key,
                {
                    **{field: row[field] for field in key_fields},
                    "received": 0,
                    "recorded": 0,
                },
            )
            entry[side] += row["total"] or 0

    report = []

    for key in sorted(data, key=lambda k: tuple(value or "" for value in k)):
        entry = data[key]
        entry["variance"] = entry["recorded"] - entry["received"]
        entry["variance_pct"] = variance_pct(entry["recorded"], entry["received"])
        report.append(entry)

    return report


def collect_serials(lines):
    """Maps each normalized serial to the line(s) it appears on."""
    found = defaultdict(list)

    rows = (
        lines
        .exclude(serial_number="")
        .values("serial_number", **SERIAL_CONTEXT_FIELDS)
    )

    for row in rows:
        text = row.pop("serial_number")
        for serial in parse_serials(text):
            found[serial].append(row)

    return found


def reconcile_serials(received, recorded):
    issues = []

    for serial in sorted(received.keys() - recorded.keys()):
        issues.append({
            "serial": serial,
            "status": "Received, not recorded",
            **received[serial][0],
        })

    for serial in sorted(recorded.keys() - received.keys()):
        issues.append({
            "serial": serial,
            "status": "Recorded, not received",
            **recorded[serial][0],
        })

    for label, found in (("received", received), ("recorded", recorded)):
        for serial, rows in sorted(found.items()):
            if len(rows) > 1:
                issues.append({
                    "serial": serial,
                    "status": f"Entered {len(rows)} times in {label}",
                    **rows[0],
                })

    summary = {
        "received_count": len(received),
        "recorded_count": len(recorded),
        "matched_count": len(received.keys() & recorded.keys()),
        "issue_count": len(issues),
    }

    return issues, summary


# =========================
# View
# =========================

def waste_report(request):

    start_date, end_date = resolve_period(request)
    period_days = (end_date - start_date).days + 1

    department_id = parse_id(request.GET.get("department"))
    project_id = parse_id(request.GET.get("project"))

    selected_department = str(department_id) if department_id else ""
    selected_project = str(project_id) if project_id else ""


    # Filters shared by all querysets
    header_filter = {"date__range": (start_date, end_date)}

    if department_id:
        header_filter["department_id"] = department_id

    line_filter = {f"waste__{key}": value for key, value in header_filter.items()}

    if project_id:
        line_filter["project_id"] = project_id


    received_lines = ReceivedWasteUnit.objects.filter(**line_filter)
    recorded_lines = ActualWasteUnit.objects.filter(**line_filter)


    # =========================
    # Weight per department (basket level, not filtered by project)
    # =========================

    received_weight = (
        ReceivedWaste.objects
        .filter(**header_filter)
        .values(department_name=F("department__name"))
        .annotate(total=Sum("waste_kg"))
        .order_by()
    )

    recorded_weight = (
        ActualWaste.objects
        .filter(**header_filter)
        .values(department_name=F("department__name"))
        .annotate(total=Sum("waste_kg"))
        .order_by()
    )

    weight_report = build_comparison(
        received_weight,
        recorded_weight,
        key_fields=["department_name"],
    )


    # =========================
    # Units per department + SKU + unit type + project
    # =========================

    received_units = (
        received_lines
        .values(**UNIT_GROUP_FIELDS)
        .annotate(total=Sum("nb_of_units"))
        .order_by()
    )

    recorded_units = (
        recorded_lines
        .values(**UNIT_GROUP_FIELDS)
        .annotate(total=Sum("nb_of_units"))
        .order_by()
    )

    units_report = build_comparison(
        received_units,
        recorded_units,
        key_fields=list(UNIT_GROUP_FIELDS),
    )


    # =========================
    # Serial number reconciliation
    # =========================

    serial_issues, serial_summary = reconcile_serials(
        collect_serials(received_lines),
        collect_serials(recorded_lines),
    )


    return render(
        request,
        "waste/waste_report.html",
        {
            "weight_report": weight_report,
            "units_report": units_report,
            "serial_issues": serial_issues,
            "serial_summary": serial_summary,

            "departments": Department.objects.order_by("name"),
            "projects": Project.objects.order_by("name"),

            "date_from": start_date,
            "date_to": end_date,
            "period_days": period_days,

            "presets": build_presets(
                start_date,
                end_date,
                {
                    "department": selected_department,
                    "project": selected_project,
                },
            ),

            "selected_department": selected_department,
            "selected_project": selected_project,
        },
    )