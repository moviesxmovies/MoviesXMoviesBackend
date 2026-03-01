from awards.serializers import AwardSerializer
from shared.serializers import BaseSerializer
from rest_framework import serializers


class PersonSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.id,
            'name': instance.name,
            'slug': instance.slug,
            'image': self.build_url(instance.image.url),
            'awards': AwardSerializer(instance.awards.all(), request=self.request).serialize(),
        }
    
    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'name': serializers.CharField(),
            'slug': serializers.CharField(),
            'image': serializers.URLField(),
            'awards': AwardSerializer.get_fields_schema(),
        }
