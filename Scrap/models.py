from django.db import models
from django.utils import timezone

def current_time():
    """Current local time, trimmed to hour and minute."""
    return timezone.localtime().time().replace(second=0, microsecond=0)

class Coil(models.Model):
    coil_number = models.CharField(
        max_length=100,
        unique=True
    )

    thickness = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    diameter = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    def __str__(self):
        return self.coil_number

class Department(models.Model):

    KG = "KG"
    UNITS = "UNITS"

    CALCULATION_TYPES = [
        (KG, "Steel Used"),
        (UNITS, "Units Produced"),
    ]

    name = models.CharField(max_length=100)

    calculation_type = models.CharField(
        max_length=10,
        choices=CALCULATION_TYPES,
        null=True,
        blank=True
    )
    uses_size = models.BooleanField(default=True)
    uses_thickness = models.BooleanField(default=False)
    uses_diameter = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class SKU(models.Model):
    name = models.CharField(max_length=100)
    departments = models.ManyToManyField(Department, related_name="skus", blank=True)
    def __str__(self):
        return self.name

class ScrapStandard(models.Model):

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT
    )

    size = models.ForeignKey(SKU, on_delete=models.PROTECT,blank=True,null=True)

    thickness = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )

    diameter = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )

    scrap_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )


    class Meta:
        unique_together = (
            "department",
            "size",
            "thickness",
            "diameter",
        )

    def __str__(self):
        return f"{self.department} - {self.scrap_percentage}%"

class ProductionEntry(models.Model):

    production_date = models.DateField()

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT
    )

    coil = models.OneToOneField(
        Coil,
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    size = models.ForeignKey(SKU, on_delete=models.PROTECT,blank=True,null=True)

    thickness = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )

    steel_used_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    units_produced = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    class Meta:
        constraints = [

            # Trimming:
            # One entry per department/date/size/thickness
            models.UniqueConstraint(
                fields=[
                    "department",
                    "production_date",
                    "size",
                    "thickness",
                ],
                condition=models.Q(
                    size__isnull=False,
                    thickness__isnull=False,
                    coil__isnull=True,
                ),
                name="unique_production_trimming",
            ),

            # Other departments:
            # One entry per department/date/size
            models.UniqueConstraint(
                fields=[
                    "department",
                    "production_date",
                    "size",
                ],
                condition=models.Q(
                    size__isnull=False,
                    thickness__isnull=True,
                    coil__isnull=True,
                ),
                name="unique_production_by_size",
            ),
        ]

    @property
    def standard(self):
        thickness = self.thickness
        diameter = None

        if self.department.uses_diameter and self.coil:
            thickness = self.coil.thickness
            diameter = self.coil.diameter

        return ScrapStandard.objects.filter(
            department=self.department,
            size=self.size,
            thickness=thickness,
            diameter=diameter,
        ).first()

class ActualScrap(models.Model):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    coil = models.ForeignKey(
        Coil,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    actual_scrap_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    entered_at = models.DateField(default=timezone.localdate)
    entered_time = models.TimeField(default=current_time)

    class Meta:
        ordering = ["-entered_at", "-entered_time"]

    def __str__(self):
        return (
            f"{self.department} - "
            f"{self.entered_at} {self.entered_time:%H:%M} - "
            f"{self.actual_scrap_kg} kg"
        )

class ReceivedScrap(models.Model):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    date = models.DateField(default=timezone.localdate)
    time = models.TimeField(default=current_time)
    received_scrap_kg = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-date", "-time"]

    def __str__(self):
        return (
            f"Received scrap from {self.department} "
            f"at {self.date} {self.time:%H:%M}"
        )