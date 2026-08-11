from django.contrib import admin
from .models import WasteUnits, ActualWaste, ReceivedWaste

admin.site.register(WasteUnits)
admin.site.register(ActualWaste)
admin.site.register(ReceivedWaste)
