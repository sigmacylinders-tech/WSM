from django.contrib import admin
from .models import WasteUnits, ActualWaste, ReceivedWaste, Project

admin.site.register(WasteUnits)
admin.site.register(ActualWaste)
admin.site.register(ReceivedWaste)
admin.site.register(Project)
