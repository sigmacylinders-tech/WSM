from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory, BaseInlineFormSet

from .models import (
    ActualWaste,
    ActualWasteUnit,
    Project,
    ReceivedWaste,
    ReceivedWasteUnit,
)


UNIT_LINE_FIELDS = ["sku", "units", "nb_of_units", "project", "serial_number"]

UNIT_LINE_WIDGETS = {
    "serial_number": forms.Textarea(
        attrs={
            "rows": 2,
            "placeholder": "Complete cylinders only, one serial per line",
        }
    ),
}


def available_projects(instance):
    """Active projects, plus the line's current project if it was deactivated."""
    current_project_id = getattr(instance, "project_id", None)
    return Project.objects.filter(
        Q(is_active=True) | Q(pk=current_project_id)
    ).order_by("name")


# =========================
# Actual Waste
# =========================

class ActualWasteForm(forms.ModelForm):
    class Meta:
        model = ActualWaste
        fields = ["department", "waste_kg", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class ActualWasteUnitForm(forms.ModelForm):
    class Meta:
        model = ActualWasteUnit
        fields = UNIT_LINE_FIELDS
        widgets = UNIT_LINE_WIDGETS

    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)

        if department is not None:
            self.fields["sku"].queryset = department.skus.order_by("name")

        self.fields["project"].queryset = available_projects(self.instance)


class BaseActualWasteUnitFormSet(BaseInlineFormSet):

    def __init__(self, *args, department=None, **kwargs):
        self.department = department
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["department"] = self.department
        return kwargs

    def clean(self):
        super().clean()

        seen = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue

            sku = form.cleaned_data.get("sku")
            unit = form.cleaned_data.get("units")
            project = form.cleaned_data.get("project")

            if sku and unit:
                key = (sku, unit, project)

                if key in seen:
                    project_label = f" and project '{project}'" if project else " with no project"
                    raise forms.ValidationError(
                        f"'{unit}' for SKU '{sku}'{project_label} was entered more than once for this basket."
                    )
                seen.add(key)


ActualWasteUnitFormSet = inlineformset_factory(
    ActualWaste,
    ActualWasteUnit,
    form=ActualWasteUnitForm,
    formset=BaseActualWasteUnitFormSet,
    fields=UNIT_LINE_FIELDS,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,  # forces at least one unit line
)


# =========================
# Received Waste
# =========================

class ReceivedWasteForm(forms.ModelForm):
    class Meta:
        model = ReceivedWaste
        fields = ["department", "waste_kg", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    # clean() removed — department+date duplicates are now expected,
    # since operators may receive multiple baskets per department per day.


class ReceivedWasteUnitForm(forms.ModelForm):
    class Meta:
        model = ReceivedWasteUnit
        fields = UNIT_LINE_FIELDS
        widgets = UNIT_LINE_WIDGETS

    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)

        if department is not None:
            self.fields["sku"].queryset = department.skus.order_by("name")

        self.fields["project"].queryset = available_projects(self.instance)


class BaseReceivedWasteUnitFormSet(BaseInlineFormSet):

    def __init__(self, *args, department=None, **kwargs):
        self.department = department
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["department"] = self.department
        return kwargs

    def clean(self):
        super().clean()

        seen = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue

            sku = form.cleaned_data.get("sku")
            unit = form.cleaned_data.get("units")
            project = form.cleaned_data.get("project")

            if sku and unit:
                key = (sku, unit, project)

                if key in seen:
                    project_label = f" and project '{project}'" if project else ""
                    raise forms.ValidationError(
                        f"'{unit}' for SKU '{sku}'{project_label} was entered more than once for this basket."
                    )
                seen.add(key)


ReceivedWasteUnitFormSet = inlineformset_factory(
    ReceivedWaste,
    ReceivedWasteUnit,
    form=ReceivedWasteUnitForm,
    formset=BaseReceivedWasteUnitFormSet,
    fields=UNIT_LINE_FIELDS,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)