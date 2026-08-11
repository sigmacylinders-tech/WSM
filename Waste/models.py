import datetime
from django.db import models

from Scrap.models import Department, SKU


class WasteUnits(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class ActualWaste(models.Model):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    waste_kg = models.FloatField()
    date = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"{self.department}-{self.waste_kg}kg-{self.date}"


class ActualWasteUnit(models.Model):
    waste = models.ForeignKey(
        ActualWaste, on_delete=models.CASCADE, related_name="unit_lines"
    )
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, null=True)
    units = models.ForeignKey(WasteUnits, on_delete=models.PROTECT)
    nb_of_units = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["waste", "sku", "units"],
                name="unique_actual_waste_unit",
            ),
        ]

    def __str__(self):
        return f"{self.sku}-{self.units} x{self.nb_of_units}"


class ReceivedWaste(models.Model):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    waste_kg = models.FloatField()
    date = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"{self.department}-{self.waste_kg}kg-{self.date}"


class ReceivedWasteUnit(models.Model):
    waste = models.ForeignKey(
        ReceivedWaste, on_delete=models.CASCADE, related_name="unit_lines"
    )
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT,null=True)
    units = models.ForeignKey(WasteUnits, on_delete=models.PROTECT)
    nb_of_units = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["waste", "sku", "units"],
                name="unique_received_waste_unit",
            ),
        ]

    def __str__(self):
        return f"{self.sku}-{self.units} x{self.nb_of_units}"