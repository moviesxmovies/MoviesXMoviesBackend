import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

COMMAND_PATH = 'movies.management.commands.generate_fixtures.Command'


def make_person(name, person_id, job=None, profile_path=None):
    p = {'id': person_id, 'name': name, 'profile_path': profile_path or f'/{name}.jpg'}
    if job:
        p['job'] = job
    return p


def make_movie_detail(movie_id=123, title='Test Movie', lang='en', **overrides):
    base = {
        'id': movie_id,
        'title': title,
        'overview': f'Synopsis in {lang}',
        'release_date': '2024-01-01',
        'poster_path': f'/{lang}_poster.jpg',
        'genres': [{'id': 28, 'name': 'Action'}, {'id': 18, 'name': 'Drama'}],
        'credits': {
            'crew': [make_person('Director One', 1001, job='Director')],
            'cast': [make_person(f'Actor {i}', 2000 + i) for i in range(1, 8)],
        },
        'watch/providers': {
            'results': {
                'ES': {
                    'flatrate': [
                        {'provider_id': 8, 'provider_name': 'Netflix', 'logo_path': '/netflix.jpg'}
                    ]
                }
            }
        },
    }
    base.update(overrides)
    return base


def make_person_detail(person_id, biography='A biography', **overrides):
    base = {
        'id': person_id,
        'biography': biography,
        'birthday': '1980-01-01',
        'deathday': None,
        'gender': 2,
    }
    base.update(overrides)
    return base


def make_image_mock():
    img_mock = MagicMock()
    img_mock.status_code = 200
    img_mock.iter_content = MagicMock(return_value=[b'fake-image-data'])
    return img_mock


def img_mocks(n):
    return [make_image_mock() for _ in range(n)]


def detail_mock(movie_id=123, title='Test Movie', lang='en', **overrides):
    m = MagicMock(status_code=200)
    m.json.return_value = make_movie_detail(movie_id, title, lang, **overrides)
    return m


def person_detail_mock(person_id, **overrides):
    m = MagicMock(status_code=200)
    m.json.return_value = make_person_detail(person_id, **overrides)
    return m


@pytest.mark.django_db
class TestFetchMoviesCommand:
    # ==================================================================
    # HELPERS
    # ==================================================================

    @pytest.fixture(autouse=True)
    def force_single_language(self):
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

    def _person_detail_mocks(self, person_ids, n_languages=1):
        """
        For each person: 1 base detail call + n_languages translation calls.
        """
        mocks = []
        for pid in person_ids:
            mocks.append(person_detail_mock(pid))  # base call (no lang)
            for _ in range(n_languages):
                mocks.append(person_detail_mock(pid))  # per-language call
        return mocks

    # ==================================================================
    # SUCCESS / ERROR
    # ==================================================================

    @patch('requests.get')
    def test_fetch_movies_success(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 123}]}

        # 1 director (id=1001) + 5 actors (ids 2001-2005)
        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        # Función de enrutamiento para el mock
        def dynamic_mock_get(url, *args, **kwargs):
            if 'movie/popular' in url:
                return mock_list
            elif '/movie/' in url:
                return detail_mock(123)
            elif '/person/' in url:
                # Extraemos el ID de la persona de la URL
                person_id_str = url.split('/person/')[1].split('?')[0]
                return person_detail_mock(int(person_id_str))
            elif 'image.tmdb.org' in url:
                return make_image_mock()

            # Fallback seguro en caso de que haga una petición no esperada
            fallback = MagicMock(status_code=404)
            fallback.json.return_value = {}
            return fallback

        # Asignamos la función en lugar de la lista concatenada
        mock_get.side_effect = dynamic_mock_get

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

            person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

            mock_get.side_effect = (
                [mock_list, detail_mock(1, 'The Movie', 'en'), detail_mock(1, 'La Película', 'es')]
                + self._person_detail_mocks(person_ids, n_languages=2)
                + img_mocks(8)  # 2 posters (per lang) + 6 persons
            )

            data, _ = self._run(tmp_path, mock_get)
            translations = self._by_model(data, 'movies.movietranslation')

            assert len(translations) == 2
            assert {t['fields']['language'] for t in translations} == {'en', 'es'}

    @patch('requests.get')
    def test_translation_stores_localised_title_and_synopsis(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

            mock_get.side_effect = (
                [
                    mock_list,
                    detail_mock(1, 'The Movie', 'en'),
                    detail_mock(1, 'La Película', 'es', overview='Sinopsis'),
                ]
                + self._person_detail_mocks(person_ids, n_languages=2)
                + img_mocks(8)
            )

            data, _ = self._run(tmp_path, mock_get)
            translations = {
                t['fields']['language']: t for t in self._by_model(data, 'movies.movietranslation')
            }
            assert translations['en']['fields']['title'] == 'The Movie'
            assert translations['es']['fields']['title'] == 'La Película'
            assert translations['es']['fields']['synopsis'] == 'Sinopsis'

    @patch('requests.get')
    def test_translation_image_path_per_language(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

            mock_get.side_effect = (
                [mock_list, detail_mock(1, lang='en'), detail_mock(1, lang='es')]
                + self._person_detail_mocks(person_ids, n_languages=2)
                + img_mocks(8)
            )

            data, _ = self._run(tmp_path, mock_get)
            for t in self._by_model(data, 'movies.movietranslation'):
                assert t['fields']['image'].startswith('movies/translations/covers/')

    @patch('requests.get')
    def test_translation_falls_back_to_primary_title_when_missing(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

            mock_get.side_effect = (
                [
                    mock_list,
                    detail_mock(1, 'Original Title', 'en'),
                    detail_mock(1, '', 'es', overview=''),
                ]
                + self._person_detail_mocks(person_ids, n_languages=2)
                + img_mocks(8)
            )

            data, _ = self._run(tmp_path, mock_get)
            es = next(
                t
                for t in self._by_model(data, 'movies.movietranslation')
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
        # 2 movies × 6 persons each, but persons are deduplicated → 6 unique persons
        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [
                mock_list,
                detail_mock(1, genres=shared_genres),
                detail_mock(2, 'Movie Two', genres=shared_genres),
            ]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(14)  # 2 posters + 6 persons (downloaded once each)
        )

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

            person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

            mock_get.side_effect = (
                [mock_list, detail_mock(1, lang='en'), es_mock]
                + self._person_detail_mocks(person_ids, n_languages=2)
                + img_mocks(8)
            )
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

        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [mock_list, detail_mock(1)]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(7)  # 1 poster + 6 persons
        )
        data, _ = self._run(tmp_path, mock_get)

        assert len(self._by_model(data, 'persons.person')) == 6

    @patch('requests.get')
    def test_persons_deduplicated_across_movies(self, mock_get, tmp_path):
        shared_cast = [make_person('Famous Actor', 9999)]
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 2}]}

        mock_get.side_effect = (
            [
                mock_list,
                detail_mock(1, credits={'crew': [], 'cast': shared_cast}),
                detail_mock(2, 'Movie Two', credits={'crew': [], 'cast': shared_cast}),
            ]
            + self._person_detail_mocks([9999], n_languages=1)  # only fetched once
            + img_mocks(3)  # 2 posters + 1 actor
        )

        data, _ = self._run(tmp_path, mock_get)
        assert len(self._by_model(data, 'persons.person')) == 1

    @patch('requests.get')
    def test_person_translations_created_per_language(self, mock_get, tmp_path):
        with patch(f'{COMMAND_PATH}.LANGUAGES', ['en', 'es']):
            mock_list = MagicMock()
            mock_list.json.return_value = {'results': [{'id': 1}]}

            person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

            mock_get.side_effect = (
                [mock_list, detail_mock(1, lang='en'), detail_mock(1, lang='es')]
                + self._person_detail_mocks(person_ids, n_languages=2)
                + img_mocks(8)
            )

            data, _ = self._run(tmp_path, mock_get)
            translations = self._by_model(data, 'persons.persontranslation')

            # 6 persons × 2 languages = 12
            assert len(translations) == 12
            assert {t['fields']['language'] for t in translations} == {'en', 'es'}

    # ==================================================================
    # PLATFORMS
    # ==================================================================

    @patch('requests.get')
    def test_platforms_deduplicated(self, mock_get, tmp_path):
        providers = {
            'results': {
                'ES': {
                    'flatrate': [
                        {'provider_id': 8, 'provider_name': 'Netflix', 'logo_path': '/netflix.jpg'}
                    ]
                }
            }
        }
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 2}]}

        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [
                mock_list,
                detail_mock(1, **{'watch/providers': providers}),
                detail_mock(2, 'Movie Two', **{'watch/providers': providers}),
            ]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(15)  # 2 posters + 6 persons + 1 platform logo
        )

        data, _ = self._run(tmp_path, mock_get)
        assert len(self._by_model(data, 'platforms.platform')) == 1

    @patch('requests.get')
    def test_movie_with_no_providers_for_es(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [mock_list, detail_mock(1, **{'watch/providers': {'results': {}}})]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(7)
        )

        data, _ = self._run(tmp_path, mock_get)
        assert self._movie(data)['fields']['platforms'] == []

    # ==================================================================
    # IMAGES
    # ==================================================================

    @patch('requests.get')
    def test_failed_image_download_uses_fallback(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [mock_list, detail_mock(1)]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + [MagicMock(status_code=500)]  # first image fails
            + img_mocks(6)
        )

        data, _ = self._run(tmp_path, mock_get)
        assert self._by_model(data, 'movies.movie')

    @patch('requests.get')
    def test_movie_with_no_poster_uses_fallback(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}]}

        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [mock_list, detail_mock(1, poster_path=None)]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(6)  # no poster call, just 6 persons
        )

        data, _ = self._run(tmp_path, mock_get)
        assert 'default.png' in self._movie(data)['fields']['cover']

    # ==================================================================
    # DUPLICATES
    # ==================================================================

    @patch('requests.get')
    def test_duplicate_movie_id_processed_only_once(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 1}]}

        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [mock_list, detail_mock(1)]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(7)
        )
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

        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [mock_list, detail_mock(1, release_date=None)]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(7)
        )
        data, _ = self._run(tmp_path, mock_get)

        assert self._movie(data)['fields']['release_date'] == '2000-01-01'

    # ==================================================================
    # PK INTEGRITY
    # ==================================================================

    @patch('requests.get')
    def test_pk_sequence_is_unique_across_multiple_movies(self, mock_get, tmp_path):
        mock_list = MagicMock()
        mock_list.json.return_value = {'results': [{'id': 1}, {'id': 2}]}

        # movies share same cast/director → persons deduplicated
        person_ids = [1001, 2001, 2002, 2003, 2004, 2005]

        mock_get.side_effect = (
            [mock_list, detail_mock(1, 'Movie One'), detail_mock(2, 'Movie Two')]
            + self._person_detail_mocks(person_ids, n_languages=1)
            + img_mocks(14)
        )

        data, _ = self._run(tmp_path, mock_get)

        for model_name in (
            'movies.movie',
            'movies.movietranslation',
            'persons.person',
            'genres.genre',
        ):
            pks = [e['pk'] for e in self._by_model(data, model_name)]
            assert len(pks) == len(set(pks)), f'Duplicate PKs in {model_name}'
