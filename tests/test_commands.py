import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

# Patch target - adjust to your actual module path
COMMAND_PATH = 'movies.management.commands.generate_fixtures.Command'


def make_movie_detail(movie_id=123, title='Test Movie', lang='en'):
    return {
        'id': movie_id,
        'title': title,
        'overview': f'Synopsis in {lang}',
        'release_date': '2024-01-01',
        'poster_path': f'/{lang}_poster.jpg',
        'genres': [{'id': 28, 'name': 'Action'}, {'id': 18, 'name': 'Drama'}],
        'credits': {
            'crew': [
                {'name': 'Director One', 'job': 'Director', 'profile_path': '/dir1.jpg'},
                {'name': 'Not A Director', 'job': 'Producer', 'profile_path': '/prod.jpg'},
            ],
            'cast': [{'name': f'Actor {i}', 'profile_path': f'/act{i}.jpg'} for i in range(1, 8)],
        },
        'watch/providers': {'results': {'ES': {'flatrate': [{'provider_name': 'Netflix'}]}}},
    }


def make_image_mock():
    img_mock = MagicMock()
    img_mock.status_code = 200
    img_mock.iter_content = MagicMock(return_value=[b'fake-image-data'])
    return img_mock


def img_mocks(n):
    return [make_image_mock() for _ in range(n)]


def detail_mock(movie_id=123, title='Test Movie', lang='en', **overrides):
    """Shorthand: returns a fully configured requests.get mock for a detail call."""
    m = MagicMock(status_code=200)
    m.json.return_value = {**make_movie_detail(movie_id, title, lang), **overrides}
    return m


@pytest.mark.django_db
class TestFetchMoviesCommand:

    # ==================================================================
    # HELPERS
    # ==================================================================

    @pytest.fixture(autouse=True)
    def force_single_language(self):
        """Patch LANGUAGES directly on the Command class so every test runs with 1 language."""
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en']):
            yield

    def _run(self, tmp_path, mock_get, pages=1):
        output_file = tmp_path / 'fixture.json'
        out = StringIO()
        call_command('generate_fixtures', pages=pages, output=str(output_file), stdout=out)
        data = json.loads(output_file.read_text()) if output_file.exists() else []
        return data, out.getvalue()

    def _by_model(self, data, model):
        return [item for item in data if item['model'] == model]

    def _movie(self, data):
        return self._by_model(data, 'movies.movie')[0]

    # ==================================================================
    # SUCCESS / ERROR
    # ==================================================================

    @patch('requests.get')
    def test_fetch_movies_success(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 123}]}

        # 1 list + 1 detail + 7 images (1 poster + 1 director + 5 actors)
        mock_get.side_effect = [mock_list, detail_mock(123)] + img_mocks(7)

        data, stdout = self._run(tmp_path, mock_get)

        movie = self._movie(data)
        assert movie['fields']['title'] == 'Test Movie'
        assert '123-test-movie' in movie['fields']['slug']
        assert 'Extraction completed' in stdout

    @patch('requests.get')
    def test_fetch_movies_api_error(self, mock_get, tmp_path):
        mock_get.side_effect = Exception('API Down')
        _, stdout = self._run(tmp_path, mock_get)
        assert 'Error on page 1' in stdout

    # ==================================================================
    # TRANSLATIONS
    # ==================================================================

    @patch('requests.get')
    def test_translation_created_per_language(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            # 1 list + 1 detail per language + 7 images + 1 extra translation poster
            mock_get.side_effect = [
                mock_list,
                detail_mock(1, 'The Movie', 'en'),
                detail_mock(1, 'La Película', 'es'),
            ] + img_mocks(8)

            data, _ = self._run(tmp_path, mock_get)
            translations = self._by_model(data, 'movies.movietranslation')

            assert len(translations) == 2
            assert {t['fields']['language'] for t in translations} == {'en', 'es'}

    @patch('requests.get')
    def test_translation_stores_localised_title_and_synopsis(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            mock_get.side_effect = [
                mock_list,
                detail_mock(1, 'The Movie', 'en'),
                detail_mock(1, 'La Película', 'es', overview='Sinopsis'),
            ] + img_mocks(8)

            data, _ = self._run(tmp_path, mock_get)
            translations = {
                t['fields']['language']: t
                for t in self._by_model(data, 'movies.movietranslation')
            }
            assert translations['en']['fields']['title'] == 'The Movie'
            assert translations['es']['fields']['title'] == 'La Película'
            assert translations['es']['fields']['synopsis'] == 'Sinopsis'

    @patch('requests.get')
    def test_translation_image_path_per_language(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            mock_get.side_effect = [
                mock_list,
                detail_mock(1, lang='en'),
                detail_mock(1, lang='es'),
            ] + img_mocks(8)

            data, _ = self._run(tmp_path, mock_get)
            for t in self._by_model(data, 'movies.movietranslation'):
                assert t['fields']['image'].startswith('movies/translations/covers/')

    @patch('requests.get')
    def test_translation_falls_back_to_primary_title_when_missing(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            mock_get.side_effect = [
                mock_list,
                detail_mock(1, 'Original Title', 'en'),
                detail_mock(1, '', 'es', overview=''),
            ] + img_mocks(8)

            data, _ = self._run(tmp_path, mock_get)
            es = next(
                t for t in self._by_model(data, 'movies.movietranslation')
                if t['fields']['language'] == 'es'
            )
            assert es['fields']['title'] == 'Original Title'

    # ==================================================================
    # GENRES
    # ==================================================================

    @patch('requests.get')
    def test_genres_deduplicated_across_movies(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 2}]}

        shared_genres = [{'id': 28, 'name': 'Action'}]
        mock_get.side_effect = [
            mock_list,
            detail_mock(1, genres=shared_genres),
            detail_mock(2, 'Movie Two', genres=shared_genres),
        ] + img_mocks(14)

        data, _ = self._run(tmp_path, mock_get)
        assert len(self._by_model(data, 'genres.genre')) == 1

    @patch('requests.get')
    def test_genre_translations_created_per_language(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            es_data = make_movie_detail(lang='es')
            es_data['genres'] = [{'id': 28, 'name': 'Acción'}, {'id': 18, 'name': 'Drama'}]
            es_mock = MagicMock(status_code=200)
            es_mock.json.return_value = es_data

            mock_get.side_effect = [mock_list, detail_mock(1, lang='en'), es_mock] + img_mocks(8)
            data, _ = self._run(tmp_path, mock_get)

            # 2 genres × 2 languages = 4
            assert len(self._by_model(data, 'genres.genretranslation')) == 4

    # ==================================================================
    # PERSONS
    # ==================================================================

    @patch('requests.get')
    def test_only_directors_and_max_5_actors_stored(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        # 1 poster + 1 director + 5 actors = 7
        mock_get.side_effect = [mock_list, detail_mock(1)] + img_mocks(7)
        data, _ = self._run(tmp_path, mock_get)

        assert len(self._by_model(data, 'persons.person')) == 6

    @patch('requests.get')
    def test_persons_deduplicated_across_movies(self, mock_get, tmp_path):
        shared_cast = [{'name': 'Famous Actor', 'profile_path': '/fa.jpg'}]
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 2}]}

        mock_get.side_effect = [
            mock_list,
            detail_mock(1, credits={'crew': [], 'cast': shared_cast}),
            detail_mock(2, 'Movie Two', credits={'crew': [], 'cast': shared_cast}),
        ] + img_mocks(3)  # 2 posters + 1 actor (downloaded once)

        data, _ = self._run(tmp_path, mock_get)
        assert len(self._by_model(data, 'persons.person')) == 1

    # ==================================================================
    # PLATFORMS
    # ==================================================================

    @patch('requests.get')
    def test_platforms_deduplicated(self, mock_get, tmp_path):
        providers = {'results': {'ES': {'flatrate': [{'provider_name': 'Netflix'}]}}}
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 2}]}

        mock_get.side_effect = [
            mock_list,
            detail_mock(1, **{'watch/providers': providers}),
            detail_mock(2, 'Movie Two', **{'watch/providers': providers}),
        ] + img_mocks(14)

        data, _ = self._run(tmp_path, mock_get)
        assert len(self._by_model(data, 'platforms.platform')) == 1

    @patch('requests.get')
    def test_movie_with_no_providers_for_es(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        mock_get.side_effect = [
            mock_list,
            detail_mock(1, **{'watch/providers': {'results': {}}}),
        ] + img_mocks(7)

        data, _ = self._run(tmp_path, mock_get)
        assert self._movie(data)['fields']['platforms'] == []

    # ==================================================================
    # IMAGES
    # ==================================================================

    @patch('requests.get')
    def test_failed_image_download_uses_fallback(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        mock_get.side_effect = [
            mock_list,
            detail_mock(1),
            MagicMock(status_code=500),  # first image fails
        ] + img_mocks(6)

        data, _ = self._run(tmp_path, mock_get)
        assert self._by_model(data, 'movies.movie')

    @patch('requests.get')
    def test_movie_with_no_poster_uses_fallback(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        mock_get.side_effect = [
            mock_list,
            detail_mock(1, poster_path=None),
        ] + img_mocks(6)  # no poster call, just 1 director + 5 actors

        data, _ = self._run(tmp_path, mock_get)
        assert 'no-image.png' in self._movie(data)['fields']['cover']

    # ==================================================================
    # DUPLICATES
    # ==================================================================

    @patch('requests.get')
    def test_duplicate_movie_id_processed_only_once(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 1}]}

        mock_get.side_effect = [mock_list, detail_mock(1)] + img_mocks(7)
        data, _ = self._run(tmp_path, mock_get)

        assert len(self._by_model(data, 'movies.movie')) == 1

    # ==================================================================
    # MISSING FIELDS
    # ==================================================================

    @patch('requests.get')
    def test_movie_missing_title_is_skipped(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        no_title = MagicMock(status_code=200)
        no_title.json.return_value = {'id': 1, 'overview': 'No title here'}

        mock_get.side_effect = [mock_list, no_title]
        data, _ = self._run(tmp_path, mock_get)
        assert self._by_model(data, 'movies.movie') == []

    @patch('requests.get')
    def test_movie_missing_release_date_defaults(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        mock_get.side_effect = [mock_list, detail_mock(1, release_date=None)] + img_mocks(7)
        data, _ = self._run(tmp_path, mock_get)

        assert self._movie(data)['fields']['release_date'] == '2000-01-01'

    # ==================================================================
    # PK INTEGRITY
    # ==================================================================

    @patch('requests.get')
    def test_pk_sequence_is_unique_across_multiple_movies(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 2}]}

        mock_get.side_effect = [
            mock_list,
            detail_mock(1, 'Movie One'),
            detail_mock(2, 'Movie Two'),
        ] + img_mocks(14)

        data, _ = self._run(tmp_path, mock_get)

        for model_name in ('movies.movie', 'movies.movietranslation', 'persons.person', 'genres.genre'):
            pks = [e['pk'] for e in self._by_model(data, model_name)]
            assert len(pks) == len(set(pks)), f'Duplicate PKs in {model_name}'