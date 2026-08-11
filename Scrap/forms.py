from django import forms
from .models import Coil, ActualScrap, ProductionEntry, ReceivedScrap


class CoilForm(forms.ModelForm):

    class Meta:
        model = Coil
        fields = [
            "coil_number",
            "thickness",
            "diameter",
        ]

        widgets = {
            "coil_number": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "thickness": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
            }),
            "diameter": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
            }),
        }


class ActualScrapForm(forms.ModelForm):

    class Meta:
        model = ActualScrap

        fields = [
            "department",
            "coil",
            "actual_scrap_kg",
            "entered_at",
        ]

        widgets = {
            "department": forms.Select(attrs={
                "class": "form-control",
                "id": "id_department",
            }),

            "coil": forms.Select(attrs={
                "class": "form-control",
                "id": "id_coil",
            }),

            "actual_scrap_kg": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),

            "entered_at": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }




class ProductionEntryForm(forms.ModelForm):

    class Meta:
        model = ProductionEntry

        fields = [
            "production_date",
            "coil",
            "size",
            "thickness",
            "steel_used_kg",
            "units_produced",
        ]

        widgets = {

            "production_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "coil": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "size": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "thickness": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "steel_used_kg": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "units_produced": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                }
            ),
        }


    def __init__(
        self,
        *args,
        department=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.department = department

        if department is None:
            return


        # -------------------------------------------------
        # Diameter departments
        # -------------------------------------------------

        if department.uses_diameter:

            # Coil is required for diameter departments.
            self.fields["coil"].required = True

            # No size.
            self.fields.pop("size")

            # No manually entered thickness.
            self.fields.pop("thickness")

            # Blanking / diameter departments use steel.
            self.fields["steel_used_kg"].required = True

            # No units.
            self.fields.pop("units_produced")


        # -------------------------------------------------
        # Non-diameter departments
        # -------------------------------------------------

        else:

            # Coil is not used.
            self.fields.pop("coil")

            # Size
            if department.uses_size:

                self.fields["size"].required = True

            else:

                self.fields.pop("size")


            # Thickness
            if department.uses_thickness:

                self.fields["thickness"].required = True

            else:

                self.fields.pop("thickness")


            # Non-diameter departments use units produced.
            self.fields["units_produced"].required = True

            # No steel used.
            self.fields.pop("steel_used_kg")

    def clean(self):

        cleaned_data = super().clean()

        if self.department is None:
            return cleaned_data

        # Existing department-specific validation
        if self.department.uses_diameter:

            if not cleaned_data.get("coil"):
                self.add_error(
                    "coil",
                    "A coil is required for this department."
                )

            if not cleaned_data.get("steel_used_kg"):
                self.add_error(
                    "steel_used_kg",
                    "Steel used is required."
                )

        else:

            if self.department.uses_size:
                if cleaned_data.get("size") is None:
                    self.add_error(
                        "size",
                        "SKU is required."
                    )

            if self.department.uses_thickness:
                if cleaned_data.get("thickness") is None:
                    self.add_error(
                        "thickness",
                        "Thickness is required."
                    )

            if cleaned_data.get("units_produced") is None:
                self.add_error(
                    "units_produced",
                    "Units produced is required."
                )

        # --------------------------------------------
        # Check duplicate production entry
        # --------------------------------------------

        if not self.errors:

            production_date = cleaned_data.get("production_date")
            size = cleaned_data.get("size")
            thickness = cleaned_data.get("thickness")

            if (
                    production_date
                    and size
                    and not self.department.uses_diameter
            ):

                queryset = ProductionEntry.objects.filter(
                    department=self.department,
                    production_date=production_date,
                    size=size,
                )

                if thickness is not None:
                    queryset = queryset.filter(
                        thickness=thickness
                    )
                else:
                    queryset = queryset.filter(
                        thickness__isnull=True
                    )

                # Don't consider the current object a duplicate when editing.
                if self.instance.pk:
                    queryset = queryset.exclude(
                        pk=self.instance.pk
                    )

                if queryset.exists():

                    if thickness is not None:

                        self.add_error(
                            None,
                            "A production entry already exists for "
                            "this department, date, SKU, and thickness."
                        )

                    else:

                        self.add_error(
                            None,
                            "A production entry already exists for "
                            "this department, date, and SKU."
                        )

        return cleaned_data


    def save(self, commit=True):

        instance = super().save(commit=False)

        instance.department = self.department


        # Make sure irrelevant fields are always cleared.

        if self.department.uses_diameter:

            instance.size = None
            instance.thickness = None
            instance.units_produced = None

        else:

            instance.coil = None
            instance.steel_used_kg = None


        if commit:
            instance.save()

        return instance

class ReceivedScrapForm(forms.ModelForm):

    class Meta:
        model = ReceivedScrap
        fields = [
            "department",
            "date",
            "received_scrap_kg",
        ]

        widgets = {
            "department": forms.Select(),
            "date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "received_scrap_kg": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        department = cleaned_data.get("department")
        date = cleaned_data.get("date")

        if department and date:

            existing = ReceivedScrap.objects.filter(
                department=department,
                date=date,
            )

            # When editing, don't consider the current object
            if self.instance.pk:
                existing = existing.exclude(
                    pk=self.instance.pk
                )

            if existing.exists():
                raise forms.ValidationError(
                    "Received scrap already exists for this department on this date."
                )

        return cleaned_data