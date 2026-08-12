from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet

from .models import (
    ActualWaste,
    ActualWasteUnit,
    ReceivedWaste,
    ReceivedWasteUnit,
)


# =========================
# Actual Waste
# =========================

class ActualWasteForm(forms.ModelForm):
    class Meta:
        model = ActualWaste
        fields = ["department", "waste_kg", "date"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class ActualWasteUnitForm(forms.ModelForm):
    class Meta:
        model = ActualWasteUnit
        fields = ["sku", "units", "nb_of_units"]

    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)

        if department is not None:
            self.fields["sku"].queryset = department.skus.order_by("name")


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

            if sku and unit:
                key = (sku, unit)

                if key in seen:
                    raise forms.ValidationError(
                        f"'{unit}' for SKU '{sku}' was entered more than once for this basket."
                    )
                seen.add(key)


ActualWasteUnitFormSet = inlineformset_factory(
    ActualWaste,
    ActualWasteUnit,
    form=ActualWasteUnitForm,
    formset=BaseActualWasteUnitFormSet,
    fields=["sku", "units", "nb_of_units"],
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
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    # clean() removed — department+date duplicates are now expected,
    # since operators may receive multiple baskets per department per day.


class ReceivedWasteUnitForm(forms.ModelForm):
    class Meta:
        model = ReceivedWasteUnit
        fields = ["sku", "units", "nb_of_units"]

    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)

        if department is not None:
            self.fields["sku"].queryset = department.skus.order_by("name")


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

            if sku and unit:
                key = (sku, unit)

                if key in seen:
                    raise forms.ValidationError(
                        f"'{unit}' for SKU '{sku}' was entered more than once for this basket."
                    )
                seen.add(key)


ReceivedWasteUnitFormSet = inlineformset_factory(
    ReceivedWaste,
    ReceivedWasteUnit,
    form=ReceivedWasteUnitForm,
    formset=BaseReceivedWasteUnitFormSet,
    fields=["sku", "units", "nb_of_units"],
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)