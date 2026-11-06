from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AccessPermission, AccessRole, Company, CompanyMembership, CustomUser, Department, Invitation


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_country', 'base_currency_code', 'work_email', 'phone')
    search_fields = ('name', 'work_email', 'phone', 'address', 'china_warehouse_address')


admin.site.register(CustomUser, UserAdmin)
admin.site.register(CompanyMembership)
admin.site.register(Department)
admin.site.register(AccessPermission)
admin.site.register(AccessRole)
admin.site.register(Invitation)
