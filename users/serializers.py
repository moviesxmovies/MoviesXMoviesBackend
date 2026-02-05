from rest_framework import serializers
from .models import User

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'boarded', 'verified')