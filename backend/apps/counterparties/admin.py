from django.contrib import admin
from .models import Counterparty, CounterpartyStatus


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'unique_code', 'address', 'qr_code_image']
    search_fields = ['name', 'type', 'unique_code', 'address', 'qr_code_image']


@admin.register(CounterpartyStatus)
class CounterpartyStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'color']
    search_fields = ['name']
