from rest_framework import serializers

from shared.serializers import BaseSerializer


class AwardSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.name,
            'slug': instance.slug,
            'category': instance.get_category_display(),
            'icon': self.build_url(instance.icon.url),
            'date': instance.date.isoformat() if instance.date else None,
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'name': serializers.CharField(),
            'slug': serializers.CharField(),
            'category': serializers.CharField(),
            'icon': serializers.URLField(),
            'date': serializers.DateField(allow_null=True),
        }
