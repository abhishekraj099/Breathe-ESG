from django.contrib import admin

from .models import AuditLog, Client, DataSource, EmissionRecord, IngestionBatch

admin.site.register(Client)
admin.site.register(DataSource)
admin.site.register(IngestionBatch)
admin.site.register(EmissionRecord)
admin.site.register(AuditLog)
