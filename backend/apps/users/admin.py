from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AccessPermission, AccessRole, Company, CompanyMembership, CustomUser, Department, Invitation

admin.site.register(CustomUser, UserAdmin)
admin.site.register(Company)
admin.site.register(CompanyMembership)
admin.site.register(Department)
admin.site.register(AccessPermission)
admin.site.register(AccessRole)
admin.site.register(Invitation)
