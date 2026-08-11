from django.contrib import admin
from .models import Department, ScrapStandard, ProductionEntry, ActualScrap, Coil, SKU

admin.site.register(Department)
admin.site.register(ScrapStandard)
admin.site.register(ProductionEntry)
admin.site.register(ActualScrap)
admin.site.register(Coil)
admin.site.register(SKU)