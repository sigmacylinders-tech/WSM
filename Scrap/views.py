from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import urlencode

from .forms import CoilForm, ActualScrapForm, ProductionEntryForm, ReceivedScrapForm
from .models import ProductionEntry, Department, ActualScrap, Coil, ReceivedScrap


def home(request):
    return render(request, "scrap/home.html")

@staff_member_required
def scrap_report(request):

    # -------------------------
    # Filters
    # -------------------------

    selected_department_id = request.GET.get("department", "")

    selected_date = request.GET.get(
        "date",
        timezone.localdate().isoformat()
    )

    # -------------------------
    # Production entries
    # -------------------------

    entries = (
        ProductionEntry.objects
        .select_related("department", "coil")
        .filter(
            production_date=selected_date
        )
        .order_by(
            "department__name",
            "production_date"
        )
    )

    if selected_department_id:
        entries = entries.filter(
            department_id=selected_department_id
        )

    # -------------------------
    # Get actual scrap entries
    # -------------------------

    actual_scrap_entries = (
        ActualScrap.objects
        .select_related("department", "coil")
        .filter(
            entered_at=selected_date
        )
    )

    if selected_department_id:
        actual_scrap_entries = actual_scrap_entries.filter(
            department_id=selected_department_id
        )

    # -------------------------
    # Calculate actual scrap
    # -------------------------

    # Blanking:
    #
    # department_id
    #     -> coil_id
    #         -> total actual scrap
    #
    # Example:
    #
    # Blanking
    #   Coil A -> 150 kg
    #   Coil B -> 120 kg
    #
    blanking_coil_totals = defaultdict(
        lambda: defaultdict(Decimal)
    )

    # Other departments:
    #
    # department_id -> total actual scrap
    #
    other_department_totals = defaultdict(Decimal)

    for actual in actual_scrap_entries:

        # -------------------------
        # Blanking
        # -------------------------

        if actual.department.uses_diameter:

            if actual.coil_id:

                blanking_coil_totals[
                    actual.department_id
                ][actual.coil_id] += actual.actual_scrap_kg

        # -------------------------
        # Other departments
        # -------------------------

        else:

            other_department_totals[
                actual.department_id
            ] += actual.actual_scrap_kg

    # -------------------------
    # Calculate production rows
    # -------------------------

    rows = []

    for entry in entries:

        standard = entry.standard

        theoretical_scrap = None

        # -------------------------
        # Calculate theoretical
        # -------------------------

        if standard:

            # KG-based departments
            # Example: Blanking
            if (
                entry.department.calculation_type == Department.KG
                and entry.steel_used_kg is not None
            ):
                theoretical_scrap = (
                    entry.steel_used_kg
                    * standard.scrap_percentage
                ) / Decimal("100")

            # Unit-based departments
            elif (
                entry.department.calculation_type == Department.UNITS
                and entry.units_produced is not None
            ):
                theoretical_scrap = (
                    entry.units_produced
                    * standard.scrap_percentage
                ) / Decimal("100")

        # -------------------------
        # Actual scrap for row
        # -------------------------

        actual_scrap = None
        row_variance = None

        # -------------------------
        # Blanking
        # -------------------------

        if entry.department.uses_diameter:

            if entry.coil_id:

                actual_scrap = blanking_coil_totals[
                    entry.department_id
                ].get(
                    entry.coil_id,
                    Decimal("0")
                )

                # Variance per coil
                if theoretical_scrap is not None:

                    row_variance = (
                        actual_scrap
                        - theoretical_scrap
                    )

        rows.append({
            "entry": entry,
            "standard": standard,
            "theoretical": theoretical_scrap,
            "actual": actual_scrap,
            "variance": row_variance,
        })

    # -------------------------
    # Group production rows
    # by department
    # -------------------------

    grouped_rows = defaultdict(list)

    for row in rows:

        grouped_rows[
            row["entry"].department
        ].append(row)

    # -------------------------
    # Build department reports
    # -------------------------

    department_reports = []

    for department, department_rows in grouped_rows.items():

        # -------------------------
        # Theoretical total
        # -------------------------

        theoretical_total = sum(
            (
                row["theoretical"]
                for row in department_rows
                if row["theoretical"] is not None
            ),
            Decimal("0")
        )

        # -------------------------
        # Actual total
        # -------------------------

        if department.uses_diameter:

            # Blanking:
            # add totals of all coils

            actual_total = sum(
                blanking_coil_totals[
                    department.id
                ].values(),
                Decimal("0")
            )

        else:

            # Other departments:
            # use department total directly

            actual_total = (
                other_department_totals[
                    department.id
                ]
            )

        # -------------------------
        # Department variance
        # -------------------------

        variance = (
            actual_total
            - theoretical_total
        )

        department_reports.append({
            "department": department,
            "rows": department_rows,

            "theoretical_total": theoretical_total,
            "actual_total": actual_total,
            "variance": variance,
        })

    # -------------------------
    # Departments with actual
    # scrap but no production
    # -------------------------

    existing_department_ids = {
        report["department"].id
        for report in department_reports
    }

    actual_department_ids = (
        set(blanking_coil_totals.keys())
        |
        set(other_department_totals.keys())
    )

    missing_departments = (
        actual_department_ids
        - existing_department_ids
    )

    if missing_departments:

        actual_departments = (
            Department.objects
            .filter(id__in=missing_departments)
        )

        for department in actual_departments:

            # -------------------------
            # Actual total
            # -------------------------

            if department.uses_diameter:

                actual_total = sum(
                    blanking_coil_totals[
                        department.id
                    ].values(),
                    Decimal("0")
                )

            else:

                actual_total = (
                    other_department_totals[
                        department.id
                    ]
                )

            # No production means
            # no theoretical scrap.

            theoretical_total = Decimal("0")

            variance = actual_total

            department_reports.append({
                "department": department,
                "rows": [],

                "theoretical_total": theoretical_total,
                "actual_total": actual_total,
                "variance": variance,
            })

    # -------------------------
    # Sort departments
    # -------------------------

    department_reports.sort(
        key=lambda report: report["department"].name
    )

    # -------------------------
    # Departments for filter
    # -------------------------

    departments = (
        Department.objects
        .all()
        .order_by("name")
    )

    # -------------------------
    # Render
    # -------------------------

    return render(
        request,
        "scrap/dashboard.html",
        {
            "department_reports": department_reports,
            "departments": departments,
            "selected_department_id": selected_department_id,
            "selected_date": selected_date,
        },
    )


def coil_list(request):

    coils = Coil.objects.all().order_by("coil_number")

    paginator = Paginator(coils, 20)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "scrap/coil_list.html",
        {
            "page_obj": page_obj,
        }
    )

def coil_create(request):

    if request.method == "POST":
        form = CoilForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("coil_list")

    else:
        form = CoilForm()

    return render(
        request,
        "scrap/coil_form.html",
        {
            "form": form,
            "title": "Create Coil",
        }
    )

def coil_edit(request, pk):

    coil = get_object_or_404(Coil, pk=pk)

    if request.method == "POST":
        form = CoilForm(request.POST, instance=coil)

        if form.is_valid():
            form.save()
            return redirect("coil_list")

    else:
        form = CoilForm(instance=coil)

    return render(
        request,
        "scrap/coil_form.html",
        {
            "form": form,
            "title": "Edit Coil",
            "coil": coil,
        }
    )

def actual_scrap_list(request):

    today = date.today()

    actual_scraps = (
        ActualScrap.objects
        .filter(entered_at=today)
        .select_related("department", "coil")
        .order_by("department__name", "coil__coil_number")
    )

    return render(
        request,
        "scrap/actual_scrap_list.html",
        {
            "actual_scraps": actual_scraps,
            "today": today,
        }
    )

def actual_scrap_create(request):

    if request.method == "POST":

        form = ActualScrapForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("actual_scrap_list")

    else:

        form = ActualScrapForm(
            initial={
                "entered_at": date.today(),
            }
        )

    return render(
        request,
        "scrap/actual_scrap_form.html",
        {
            "form": form,
            "title": "Create Actual Scrap",
        }
    )

def actual_scrap_edit(request, pk):

    actual_scrap = get_object_or_404(
        ActualScrap,
        pk=pk
    )

    if request.method == "POST":

        form = ActualScrapForm(
            request.POST,
            instance=actual_scrap
        )

        if form.is_valid():
            form.save()
            return redirect("actual_scrap_list")

    else:

        form = ActualScrapForm(
            instance=actual_scrap
        )

    return render(
        request,
        "scrap/actual_scrap_form.html",
        {
            "form": form,
            "title": "Edit Actual Scrap",
            "actual_scrap": actual_scrap,
        }
    )

def production_department_list(request):
    departments = Department.objects.exclude(
        calculation_type__isnull=True
    ).order_by("name")

    return render(
        request,
        "scrap/department_list.html",
        {
            "departments": departments,
        }
    )

def production_entry_list(request, department_id):

    department = get_object_or_404(
        Department,
        pk=department_id
    )

    selected_date = request.GET.get("date")

    if selected_date:
        try:
            selected_date = date.fromisoformat(selected_date)
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    production_entries = (
        ProductionEntry.objects
        .filter(
            department=department,
            production_date=selected_date
        )
        .select_related("coil")
        .order_by("id")
    )

    return render(
        request,
        "scrap/production_entry_list.html",
        {
            "department": department,
            "production_entries": production_entries,
            "selected_date": selected_date,
        }
    )


def production_entry_create(
    request,
    department_id
):

    department = get_object_or_404(
        Department,
        pk=department_id
    )


    if request.method == "POST":

        form = ProductionEntryForm(
            request.POST,
            department=department
        )

        if form.is_valid():

            form.save()

            return redirect(
                "production_entry_list",
                department_id=department.pk
            )


    else:

        form = ProductionEntryForm(
            department=department,
            initial={
                "production_date": date.today(),
            }
        )


    return render(
        request,
        "scrap/production_entry_form.html",
        {
            "form": form,
            "department": department,
            "title": "Create Production Entry",
        }
    )


def production_entry_edit(
    request,
    pk
):

    production_entry = get_object_or_404(
        ProductionEntry,
        pk=pk
    )

    department = production_entry.department


    if request.method == "POST":

        form = ProductionEntryForm(
            request.POST,
            instance=production_entry,
            department=department
        )

        if form.is_valid():

            form.save()

            return redirect(
                "production_entry_list",
                department_id=department.pk
            )


    else:

        form = ProductionEntryForm(
            instance=production_entry,
            department=department
        )


    return render(
        request,
        "scrap/production_entry_form.html",
        {
            "form": form,
            "department": department,
            "production_entry": production_entry,
            "title": "Edit Production Entry",
        }
    )

def received_scrap_list(request):
    selected_date = parse_date(request.GET.get("date") or "") or timezone.localdate()

    received_scraps = (
        ReceivedScrap.objects
        .select_related("department")
        .filter(date=selected_date)
        .order_by("department__name", "time")
    )

    total_kg = received_scraps.aggregate(total=Sum("received_scrap_kg"))["total"]

    return render(
        request,
        "scrap/received_scrap_list.html",
        {
            "received_scraps": received_scraps,
            "selected_date": selected_date.isoformat(),
            "total_kg": total_kg,
        },
    )

def received_scrap_create(request):
    if request.method == "POST":
        form = ReceivedScrapForm(request.POST)
        if form.is_valid():
            scrap = form.save()
            return redirect(f"{reverse('received_scrap_list')}?date={scrap.date.isoformat()}")
    else:
        form = ReceivedScrapForm()  # date and time pre-filled from model defaults

    return render(
        request,
        "scrap/received_scrap_form.html",
        {"form": form, "title": "Add Received Scrap"},
    )

def received_scrap_edit(request, pk):
    received_scrap = get_object_or_404(ReceivedScrap, pk=pk)

    if request.method == "POST":
        form = ReceivedScrapForm(request.POST, instance=received_scrap)
        if form.is_valid():
            scrap = form.save()
            return redirect(f"{reverse('received_scrap_list')}?date={scrap.date.isoformat()}")
    else:
        form = ReceivedScrapForm(instance=received_scrap)

    return render(
        request,
        "scrap/received_scrap_form.html",
        {"form": form, "title": "Edit Received Scrap"},
    )


# =========================================================
# Helpers
# =========================================================

def _parse_date(value):
    """Parse YYYY-MM-DD safely. Returns a date or None."""

    if not value:
        return None

    try:
        return date.fromisoformat(value.strip())
    except (TypeError, ValueError):
        return None


def _month_bounds(year, month):
    """First and last day of a given month."""

    return (
        date(year, month, 1),
        date(year, month, monthrange(year, month)[1]),
    )


def _resolve_period(request):
    """
    Work out the reporting period from the query string.

    Priority:
        1. ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
           (either side may be missing)
        2. ?month=YYYY-MM  (kept for old links / bookmarks)
        3. Current month
    """

    today = timezone.localdate()

    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))

    # -------------------------
    # 1. Explicit date range
    # -------------------------

    if date_from or date_to:

        if date_from and not date_to:
            # From a date until today (or the same day if in the future)
            date_to = today if date_from <= today else date_from

        elif date_to and not date_from:
            # From the start of that month until the given date
            date_from = date_to.replace(day=1)

        # Swap if the user entered them backwards
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        return date_from, date_to

    # -------------------------
    # 2. Legacy month filter
    # -------------------------

    selected_month = request.GET.get("month")

    if selected_month:

        try:
            year, month = map(int, selected_month.split("-"))
            return _month_bounds(year, month)

        except (ValueError, TypeError):
            pass

    # -------------------------
    # 3. Default: current month
    # -------------------------

    return _month_bounds(today.year, today.month)


def _build_presets(date_from, date_to, selected_department_id):
    """Quick-select ranges shown above the table."""

    today = timezone.localdate()

    this_month_start, this_month_end = _month_bounds(
        today.year,
        today.month,
    )

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
        }

        if selected_department_id:
            params["department"] = selected_department_id

        presets.append({
            "label": label,
            "query": urlencode(params),
            "active": (start == date_from and end == date_to),
        })

    return presets


# =========================================================
# View
# =========================================================
@staff_member_required
def monthly_scrap_report(request):
    # -------------------------
    # Period filter
    # -------------------------

    date_from, date_to = _resolve_period(request)

    period_days = (date_to - date_from).days + 1

    # -------------------------
    # Department filter
    # -------------------------

    selected_department_id = request.GET.get(
        "department",
        "",
    ).strip()

    # Ignore anything that isn't a valid id
    if not selected_department_id.isdigit():
        selected_department_id = ""

    # -------------------------
    # Production entries
    # -------------------------

    production_entries = (
        ProductionEntry.objects
        .select_related(
            "department",
            "coil",
            "size",
        )
        .filter(
            production_date__gte=date_from,
            production_date__lte=date_to,
        )
    )

    if selected_department_id:
        production_entries = production_entries.filter(
            department_id=selected_department_id
        )

    # -------------------------
    # Calculate theoretical
    # -------------------------

    theoretical_totals = defaultdict(Decimal)

    for entry in production_entries:

        standard = entry.standard

        if not standard:
            continue

        theoretical_scrap = None

        # KG-based departments
        if (
                entry.department.calculation_type == Department.KG
                and entry.steel_used_kg is not None
        ):

            theoretical_scrap = (
                                        entry.steel_used_kg
                                        * standard.scrap_percentage
                                ) / Decimal("100")

        # Unit-based departments
        elif (
                entry.department.calculation_type == Department.UNITS
                and entry.units_produced is not None
        ):

            theoretical_scrap = (
                                        Decimal(entry.units_produced)
                                        * standard.scrap_percentage
                                ) / Decimal("100")

        if theoretical_scrap is not None:
            theoretical_totals[
                entry.department_id
            ] += theoretical_scrap

    # -------------------------
    # Actual scrap
    # -------------------------

    actual_scrap_entries = (
        ActualScrap.objects
        .select_related("department")
        .filter(
            entered_at__gte=date_from,
            entered_at__lte=date_to,
        )
    )

    if selected_department_id:
        actual_scrap_entries = actual_scrap_entries.filter(
            department_id=selected_department_id
        )

    actual_totals = defaultdict(Decimal)

    for actual in actual_scrap_entries:

        if actual.actual_scrap_kg is not None:
            actual_totals[
                actual.department_id
            ] += actual.actual_scrap_kg

    # -------------------------
    # Received scrap
    # -------------------------

    received_scrap_entries = (
        ReceivedScrap.objects
        .select_related("department")
        .filter(
            date__gte=date_from,
            date__lte=date_to,
        )
    )

    if selected_department_id:
        received_scrap_entries = received_scrap_entries.filter(
            department_id=selected_department_id
        )

    received_totals = defaultdict(Decimal)

    for received in received_scrap_entries:

        if received.received_scrap_kg is not None:
            received_totals[
                received.department_id
            ] += received.received_scrap_kg

    # -------------------------
    # Departments in report
    # -------------------------

    department_ids = (
            set(theoretical_totals.keys())
            | set(actual_totals.keys())
            | set(received_totals.keys())
    )

    departments = (
        Department.objects
        .filter(id__in=department_ids)
        .order_by("name")
    )

    # -------------------------
    # Build report
    # -------------------------

    department_reports = []

    total_theoretical = Decimal("0")
    total_actual = Decimal("0")
    total_received = Decimal("0")

    for department in departments:
        theoretical = theoretical_totals[department.id]
        actual = actual_totals[department.id]
        received = received_totals[department.id]

        department_reports.append({
            "department": department,

            "theoretical": theoretical,
            "actual": actual,
            "received": received,

            "actual_vs_theoretical": actual - theoretical,
            "actual_vs_received": actual - received,
        })

        total_theoretical += theoretical
        total_actual += actual
        total_received += received

    # -------------------------
    # Totals
    # -------------------------

    total_actual_vs_theoretical = (
            total_actual - total_theoretical
    )

    total_actual_vs_received = (
            total_actual - total_received
    )

    # -------------------------
    # Departments for filter
    # -------------------------

    all_departments = (
        Department.objects
        .all()
        .order_by("name")
    )

    # -------------------------
    # Render
    # -------------------------

    return render(
        request,
        "scrap/monthly_scrap_report.html",
        {
            "department_reports": department_reports,

            "total_theoretical": total_theoretical,
            "total_actual": total_actual,
            "total_received": total_received,

            "total_actual_vs_theoretical":
                total_actual_vs_theoretical,

            "total_actual_vs_received":
                total_actual_vs_received,

            "departments": all_departments,

            "selected_department_id": selected_department_id,

            "date_from": date_from,
            "date_to": date_to,
            "period_days": period_days,

            "presets": _build_presets(
                date_from,
                date_to,
                selected_department_id,
            ),
        },
    )