from django.db import models
from django.utils.crypto import get_random_string
from core.models import BaseModel, ChangeLog
from users.models import Company, CustomUser


class CounterpartyStatus(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='counterparty_statuses',
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, null=True, blank=True)
    translations = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#999999')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_counterparty_status_per_company'),
            models.UniqueConstraint(fields=['company', 'code'], name='unique_counterparty_status_code_per_company'),
        ]

    def display_name(self, language=None):
        from core.statuses import status_display_name
        return status_display_name(self, language)

    def __str__(self):
        return self.name


class Counterparty(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='counterparties'
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=[('china', 'Chinese'), ('local', 'Local')])
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    unique_code = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True, null=True)
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    source = models.CharField(max_length=255, blank=True)
    status = models.ForeignKey(CounterpartyStatus, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.unique_code:
            prefix = 'CN' if self.type == 'china' else 'LC'
            random_part = get_random_string(6).upper()
            self.unique_code = f'{prefix}-{random_part}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'unique_code'], name='unique_counterparty_code_per_company'),
        ]


class CounterpartyChangeLog(ChangeLog):
    counterparty = models.ForeignKey(
        'Counterparty',
        on_delete=models.CASCADE,
        related_name='history'
    )

    def __str__(self):
        return f"{self.counterparty.name}: {self.field_name} changed"
