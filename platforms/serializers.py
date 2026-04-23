from rest_framework import serializers

from shared.serializers import BaseSerializer


class PlatformSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.name,
            'slug': instance.slug,
            'url': instance.url,
            'image': self.build_url(instance.image.url)
            if instance.image and self.request
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'name': serializers.CharField(),
            'slug': serializers.CharField(),
            'url': serializers.URLField(),
            'image': serializers.URLField(allow_null=True),
        }
