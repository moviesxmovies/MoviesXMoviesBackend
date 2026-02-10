from rest_framework import serializers

from shared.serializers import BaseSerializer

from .models import User


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'boarded', 'verified')


class UserSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'username': instance.username,
            'bio': instance.bio,
            'following': instance.is_followed_by(self.request.user) if self.request and self.request.user else None,
        }
