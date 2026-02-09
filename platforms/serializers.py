from shared.serializers import BaseSerializer


class PlatformSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'name': instance.name,
            'slug': instance.slug,
            'url': instance.url,
        }
