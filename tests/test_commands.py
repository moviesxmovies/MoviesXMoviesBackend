import json
import os
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestFetchMoviesCommand:
    @patch('requests.get')
    def test_fetch_movies_success(self, mock_get, tmp_path):
        # 1. Configuramos el mock para la lista de películas (Página 1)
        mock_list_response = MagicMock()
        mock_list_response.json.return_value = {'results': [{'id': 123}]}

        # 2. Configuramos el mock para el detalle de la película
        mock_detail_response = MagicMock()
        mock_detail_response.status_code = 200
        mock_detail_response.json.return_value = {
            'id': 123,
            'title': 'Test Movie',
            'overview': 'Sinopsis de prueba',
            'release_date': '2024-01-01',
            'poster_path': '/test_poster.jpg',
            'genres': [{'name': 'Drama'}],
            'credits': {
                'crew': [{'name': 'Director Test', 'job': 'Director', 'profile_path': '/dir.jpg'}],
                'cast': [{'name': 'Actor Test', 'profile_path': '/act.jpg'}],
            },
            'watch/providers': {'results': {'ES': {'flatrate': [{'provider_name': 'Netflix'}]}}},
        }

        # Simulamos las llamadas secuenciales a requests.get
        mock_get.side_effect = [
            mock_list_response,
            mock_detail_response,
            MagicMock(status_code=200),
        ]

        # 3. Definimos rutas temporales para no ensuciar el proyecto
        output_file = tmp_path / 'test_fixture.json'

        # Ejecutamos el comando
        out = StringIO()
        call_command('generate_fixtures', pages=1, output=str(output_file), stdout=out)

        # 4. Verificaciones
        assert os.path.exists(output_file)

        with open(output_file, 'r') as f:
            data = json.load(f)

        # Verificamos que se crearon los 4 tipos de modelos
        models = [item['model'] for item in data]
        assert 'genres.genre' in models
        assert 'persons.person' in models
        assert 'platforms.platform' in models
        assert 'movies.movie' in models

        # Verificar datos específicos de la película
        movie_entry = next(item for item in data if item['model'] == 'movies.movie')
        assert movie_entry['fields']['title'] == 'Test Movie'
        assert '123-test-movie' in movie_entry['fields']['slug']

        assert 'Extraction completed' in out.getvalue()

    @patch('requests.get')
    def test_fetch_movies_api_error(self, mock_get, tmp_path):
        mock_get.side_effect = Exception('API Down')

        output_file = tmp_path / 'error_fixture.json'
        out = StringIO()

        # No debería lanzar excepción hacia afuera
        call_command('generate_fixtures', pages=1, output=str(output_file), stdout=out)

        assert 'Error on page 1' in out.getvalue()
