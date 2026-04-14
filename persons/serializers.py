from rest_framework import serializers

from awards.serializers import AwardSerializer
from shared.serializers import BaseSerializer


class PersonSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.id,
            'name': instance.name,
            'slug': instance.slug,
            'image': self.build_url(instance.image.url),
            'awards': AwardSerializer(instance.awards.all(), request=self.request).serialize(),
            'biography': instance.translate_biography(self.request.user.preferred_language)
            if self.request
            else instance.biography,
            'birthday': instance.birthday.isoformat() if instance.birthday else None,
            'deathday': instance.deathday.isoformat() if instance.deathday else None,
            'gender': instance.gender,
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'name': serializers.CharField(),
            'slug': serializers.CharField(),
            'image': serializers.URLField(),
            'awards': AwardSerializer.get_fields_schema(),
            'biography': serializers.CharField(),
            'birthday': serializers.DateField(allow_null=True),
            'deathday': serializers.DateField(allow_null=True),
            'gender': serializers.IntegerField(),
        }
