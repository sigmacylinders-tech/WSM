from django.contrib import admin
from .models import Department, ScrapStandard, ProductionEntry, ActualScrap, Coil, SKU, ReceivedScrap

admin.site.register(Department)
admin.site.register(ScrapStandard)
admin.site.register(ProductionEntry)
admin.site.register(ActualScrap)
admin.site.register(ReceivedScrap)
admin.site.register(Coil)
admin.site.register(SKU)