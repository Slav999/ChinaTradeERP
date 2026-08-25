from django.db import migrations


DEFAULT_PRODUCT_UNITS = ('pcs', 'kg', 'g', 'm', 'm2', 'm3', 'box', 'set')
DEFAULT_PRODUCT_CATEGORIES = (('General', None),)


def forwards(apps, schema_editor):
    Company = apps.get_model('users', 'Company')
    Product = apps.get_model('products', 'Product')
    ProductCategory = apps.get_model('products', 'ProductCategory')
    Unit = apps.get_model('products', 'Unit')

    companies = list(Company.objects.all())
    fallback_company = companies[0] if companies else None

    global_categories = list(ProductCategory.objects.filter(company__isnull=True))
    global_units = list(Unit.objects.filter(company__isnull=True))

    for category in global_categories:
        for company in companies:
            ProductCategory.objects.get_or_create(
                company=company,
                name=category.name,
                defaults={'margin_pct': category.margin_pct},
            )

    for unit in global_units:
        for company in companies:
            Unit.objects.get_or_create(company=company, name=unit.name)

    for product in Product.objects.select_related('supplier', 'created_by', 'category', 'unit').all():
        company = product.company
        if not company:
            company = getattr(product.supplier, 'company', None) or getattr(product.created_by, 'company', None) or fallback_company
            if company:
                product.company = company

        if company and product.category_id and product.category.company_id != company.id:
            category, _ = ProductCategory.objects.get_or_create(
                company=company,
                name=product.category.name,
                defaults={'margin_pct': product.category.margin_pct},
            )
            product.category = category

        if company and product.unit_id and product.unit.company_id != company.id:
            unit, _ = Unit.objects.get_or_create(company=company, name=product.unit.name)
            product.unit = unit

        product.save(update_fields=['company', 'category', 'unit'])

    for company in companies:
        for name, margin_pct in DEFAULT_PRODUCT_CATEGORIES:
            ProductCategory.objects.get_or_create(
                company=company,
                name=name,
                defaults={'margin_pct': margin_pct},
            )
        for name in DEFAULT_PRODUCT_UNITS:
            Unit.objects.get_or_create(company=company, name=name)

    ProductCategory.objects.filter(company__isnull=True).delete()
    Unit.objects.filter(company__isnull=True).delete()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0015_product_company_productcategory_company_and_more'),
        ('counterparties', '0006_scope_counterparty_data_to_companies'),
        ('users', '0011_company_base_currency_code_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
