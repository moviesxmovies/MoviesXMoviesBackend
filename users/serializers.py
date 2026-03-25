from django.urls import reverse
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
            'is_friend': instance.is_friend(self.request.user)
            if self.request and self.request.user and self.request.user != instance
            else None,
            'requested_friendship_status': instance.get_friend_request_status(self.request.user)
            if self.request and self.request.user and self.request.user != instance
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
            'is_friend': serializers.BooleanField(allow_null=True),
            'requested_friendship_status': serializers.CharField(allow_null=True),
            'picture': serializers.URLField(allow_null=True),
        }


class FriendRequestSerializer(BaseSerializer):
    def serialize_instance(self, instance) -> dict:
        return {
            'id': instance.pk,
            'from_user': self.build_url(reverse('user-detail', args={instance.from_user})),
            'to_user': self.build_url(reverse('user-detail', args={instance.to_user})),
            'status': instance.get_status_display(),
        }

    @staticmethod
    def get_fields_dict():
        return {
            'id': serializers.IntegerField(),
            'from_user': serializers.URLField(),
            'to_user': serializers.URLField(),
            'status': serializers.CharField(),
        }
