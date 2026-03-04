from rest_framework import serializers

from shared.serializers import BaseSerializer


class GenreSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.translate_name(self.request.user.preferred_language)
            if self.request
            else instance.name,
            'slug': instance.slug,
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'name': serializers.CharField(),
            'slug': serializers.CharField(),
        }
