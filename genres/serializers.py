from shared.serializers import BaseSerializer
from rest_framework import serializers


class GenreSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.name,
            'slug': instance.slug,
        }
    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'name': serializers.CharField(),
            'slug': serializers.CharField(),
        }
