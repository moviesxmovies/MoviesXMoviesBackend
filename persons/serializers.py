from shared.serializers import BaseSerializer


class PersonSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.id,
            'name': instance.name,
            'slug': instance.slug,
            'image': self.build_url(instance.image.url),
            'country': instance.get_country_display(),
        }
