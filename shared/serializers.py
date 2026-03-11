import json
from abc import ABC
from typing import Iterable

from django.http import HttpRequest, JsonResponse
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer for obtaining JWT token pairs (access and refresh tokens) that includes additional user information in the token payload.
    This serializer extends the default TokenObtainPairSerializer provided by the Simple JWT library, allowing for customization of the token generation process to include fields such as username, boarded status, verified status, and preferred language of the user.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['username'] = user.username
        token['boarded'] = user.boarded
        token['verified'] = user.verified

        return token


class BaseSerializer(ABC):
    """
    Base serializer class that provides a structure for serializing objects or iterables of objects into JSON format. This class includes methods for building absolute URLs, serializing individual instances, and generating JSON responses. It also provides class methods for defining the schema of the serialized data, which can be used for documentation purposes with tools like drf-spectacular.
    """
    def __init__(
        self,
        to_serialize: object | Iterable[object],
        *,
        fields: Iterable[str] = None,
        request: HttpRequest = None,
    ):
        self.to_serialize = to_serialize
        self.fields = fields
        self.request = request
        self.fields = set(fields) if fields else set()

    def build_url(self, path: str) -> str:
        return self.request.build_absolute_uri(path) if self.request else path

    def serialize_instance(self, instance: object) -> dict:
        raise NotImplementedError

    def __serialize_instance(self, instance: object) -> dict:
        serialized = self.serialize_instance(instance)
        return {f: v for f, v in serialized.items() if not self.fields or f in self.fields}

    def serialize(self) -> dict | list[dict]:
        if not isinstance(self.to_serialize, Iterable):
            return self.__serialize_instance(self.to_serialize)
        return [self.__serialize_instance(instance) for instance in self.to_serialize]

    def to_json(self) -> str:
        return json.dumps(self.serialize())

    def json_response(self) -> JsonResponse:
        return JsonResponse(self.serialize(), safe=False)

    @classmethod
    def get_schema(cls, name: str = None):
        return inline_serializer(name=name or cls.__name__, fields=cls.get_fields_schema())

    @classmethod
    def get_fields_schema(cls, many=False) -> dict | serializers.ListSerializer:
        fields = cls.get_fields_dict()

        if many:
            return serializers.ListSerializer(
                child=inline_serializer(name=f'{cls.__name__}Item', fields=fields)
            )
        return fields

    @classmethod
    def get_fields_dict(cls) -> dict:
        raise NotImplementedError

    @classmethod
    def get_paginated_schema(cls, name: str = None):
        return inline_serializer(
            name=f'Paginated{name or cls.__name__}',
            fields={
                'results': cls.get_fields_schema(many=True),
                'total_pages': serializers.IntegerField(),
                'count': serializers.IntegerField(),
                'has_next': serializers.BooleanField(),
                'has_previous': serializers.BooleanField(),
                'current_page': serializers.IntegerField(),
            },
        )
