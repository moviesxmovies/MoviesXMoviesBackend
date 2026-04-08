from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view

from persons.models import Person
from persons.serializers import PersonSerializer
from shared.decorators import cached_view
from users.decorators import auth_required


@extend_schema(
    responses={
        200: PersonSerializer.get_schema(),
        404: OpenApiResponse(description='Person not found.'),
    },
)
@api_view(['GET'])
@auth_required
@cached_view(lambda req, person: f'person_detail:{person.pk}', timeout=60 * 60 * 24)
def person_detail(request, person: Person):
    return PersonSerializer(person, request=request).json_response()
