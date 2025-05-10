from django.db import models
from django.utils.crypto import get_random_string


class CounterpartyStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#999999')

    def __str__(self):
        return self.name


class Counterparty(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=[('china', 'Chinese'), ('local', 'Local')])
    unique_code = models.CharField(max_length=50, unique=True, blank=True)
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
