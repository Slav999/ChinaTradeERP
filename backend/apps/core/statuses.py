def normalize_language(language):
    return 'en' if str(language or '').lower().startswith('en') else 'ru'


def request_language(request, company=None):
    user = getattr(request, 'user', None)
    language = getattr(user, 'notification_language', None)
    if not language and company is not None:
        language = getattr(company, 'language_code', None)
    return normalize_language(language)


def status_display_name(status, language=None):
    if status is None:
        return ''
    language = normalize_language(language)
    translations = getattr(status, 'translations', None) or {}
    preferred = translations.get(language, '')
    alternative = translations.get('ru' if language == 'en' else 'en', '')
    return preferred or alternative or status.name


class TranslatableStatusSerializerMixin:
    """Shared API behaviour for company-editable, bilingual statuses."""

    def get_display_name(self, obj):
        request = self.context.get('request')
        return obj.display_name(request_language(request, obj.company))

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        company = getattr(getattr(request, 'user', None), 'company', None)
        if self.instance is not None:
            company = self.instance.company

        name = (attrs.get('name') or getattr(self.instance, 'name', '') or '').strip()
        current_translations = dict(getattr(self.instance, 'translations', None) or {})
        translations = attrs.get('translations', current_translations) or {}
        translations = {
            str(code).lower(): str(value).strip()
            for code, value in translations.items()
            if str(value).strip()
        }
        name_en = translations.get('en', '')
        name_ru = translations.get('ru', '')
        language = request_language(request, company)

        if not name_en and not name_ru and name:
            if language == 'en':
                name_en = name
            else:
                name_ru = name
        if not name:
            name = (name_en if language == 'en' else name_ru) or name_en or name_ru
        if not name:
            from rest_framework import serializers
            raise serializers.ValidationError({'name': 'Enter a status name in at least one language.'})

        if company is not None:
            from django.db.models import Q
            from rest_framework import serializers

            duplicate = self.Meta.model.objects.filter(company=company).filter(
                Q(name__iexact=name)
            )
            if self.instance is not None:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError({'name': 'Status already exists.'})

        attrs['name'] = name
        attrs['translations'] = translations
        return attrs
