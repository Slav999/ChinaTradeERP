from django.db import models
from django.conf import settings
from django.db import transaction


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated"
    )

    class Meta:
        abstract = True


class OrderNumberSequence(models.Model):
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE)
    kind = models.CharField(max_length=32)
    year = models.PositiveIntegerField()
    last_number = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['company', 'kind', 'year'], name='unique_annual_order_sequence')]


class AnnualOrderModel(BaseModel):
    order_year = models.PositiveIntegerField(editable=False)

    class Meta:
        abstract = True

    @property
    def is_previous_year(self):
        from .order_numbering import company_year
        return self.order_year < company_year(self.company)

    def number_sequence_kind(self):
        return self._meta.model_name

    def number_sequence_orders(self):
        return type(self).objects.all()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            return super().save(*args, **kwargs)
        from users.models import Company
        from .order_numbering import company_year
        with transaction.atomic():
            # The company row also serializes first-use creation of the counter.
            company = Company.objects.select_for_update().get(pk=self.company_id)
            self.order_year = company_year(company)
            sequence, created = OrderNumberSequence.objects.get_or_create(
                company=company, kind=self.number_sequence_kind(), year=self.order_year,
            )
            if created:
                numbers = self.number_sequence_orders().filter(company=company, order_year=self.order_year).values_list('order_number', flat=True)
                sequence.last_number = max((int(n) for n in numbers if n.isascii() and n.isdigit()), default=0)
            if not self.order_number:
                self.order_number = str(sequence.last_number + 1)
            if self.order_number.isascii() and self.order_number.isdigit():
                sequence.last_number = max(sequence.last_number, int(self.order_number))
            sequence.save(update_fields=['last_number'])
            return super().save(*args, **kwargs)


class ChangeLog(models.Model):
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_changes'
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['-changed_at']
