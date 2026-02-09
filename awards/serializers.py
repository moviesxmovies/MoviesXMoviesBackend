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
