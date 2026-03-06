from rest_framework import serializers

from shared.serializers import BaseSerializer

from .models import User


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'boarded', 'verified', 'preferred_language')


class UserSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'username': instance.username,
            'bio': instance.bio,
            'following': instance.is_followed_by(self.request.user)
            if self.request and self.request.user
            else None,
            'picture': self.build_url(instance.picture.url)
            if instance.picture and self.request
            else None,
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'username': serializers.CharField(),
            'bio': serializers.CharField(),
            'following': serializers.BooleanField(allow_null=True),
            'picture': serializers.URLField(allow_null=True),
        }
