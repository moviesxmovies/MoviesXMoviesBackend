import json
import os
import time
from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from prettyconf import config

from main import settings


class Command(BaseCommand):
    help = (
        'Generates fixture data for movies, genres, platforms, and persons by fetching from TMDB API. '
        'Usage: python manage.py generate_fixtures --pages <number_of_pages> --output <output_file.json>'
    )

    BASE_URL = 'https://api.themoviedb.org/3'
    MEDIA_ROOT = 'media'
    MOVIE_SUBDIR = 'movies/covers'
    MOVIE_TRANSLATION_SUBDIR = 'movies/translations/covers'
    PERSON_SUBDIR = 'person'

    # Languages to fetch translations for.
    # The first language is used as the primary (stored in the main model fields).
    # All languages get a Translation record.
    LANGUAGES = settings.SUPPORTED_LANGUAGES

    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            type=int,
            default=1,
            help='Number of pages to fetch from TMDB (20 movies per page)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='movie_fixtures_test.json',
            help='Exit path for the generated fixture file',
        )

    def handle(self, *args, **options):
        self.api_key = config('TMDB_API_KEY', default='')
        self.headers = {'Authorization': f'Bearer {self.api_key}'}

        self.now = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

        self.processed_movie_ids = set()
        self.pks = {
            'movie': 1,
            'movie_translation': 1,
            'person': {},
            'genre': {},
            'genre_translation': 1,
            'platform': {},
        }
        self.fixtures = {
            'genres': [],
            'genre_translations': [],
            'persons': [],
            'platforms': [],
            'movies': [],
            'movie_translations': [],
        }

        self.setup_directories()

        pages = options['pages']
        self.stdout.write(self.style.NOTICE(f'Starting extraction of {pages} pages...'))

        for page in range(1, pages + 1):
            self.process_page(page)

        final_data = (
            self.fixtures['genres']
            + self.fixtures['genre_translations']
            + self.fixtures['persons']
            + self.fixtures['platforms']
            + self.fixtures['movies']
            + self.fixtures['movie_translations']
        )

        with open(options['output'], 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(f'Extraction completed: {len(self.fixtures["movies"])} movies')
        )

    def setup_directories(self):
        for subdir in [self.MOVIE_SUBDIR, self.MOVIE_TRANSLATION_SUBDIR, self.PERSON_SUBDIR]:
            os.makedirs(os.path.join(self.MEDIA_ROOT, subdir), exist_ok=True)

    def download_image(self, path, subdir):
        if not path:
            return f'{subdir}/no-image.png'

        filename = path.lstrip('/')
        full_path = os.path.join(self.MEDIA_ROOT, subdir, filename)
        db_path = f'{subdir}/{filename}'

        if not os.path.exists(full_path):
            try:
                url = f'https://image.tmdb.org/t/p/w500/{path}'
                res = requests.get(url, stream=True, timeout=10)
                if res.status_code == 200:
                    with open(full_path, 'wb') as f:
                        for chunk in res.iter_content(1024):
                            f.write(chunk)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error downloading image {url}: {e}'))
                return f'{subdir}/no-image.png'
        return db_path

    def fetch_movie_detail(self, movie_id, language):
        """Fetch full movie detail for a given language."""
        url = (
            f'{self.BASE_URL}/movie/{movie_id}'
            f'?append_to_response=credits,watch/providers&language={language}-{language.upper()}'
        )
        return requests.get(url, headers=self.headers).json()

    def process_page(self, page):
        # Discover popular movies using the primary language
        primary_lang = self.LANGUAGES[0]
        url = f'{self.BASE_URL}/movie/popular?language={primary_lang}-{primary_lang.upper()}&page={page}'
        try:
            response = requests.get(url, headers=self.headers)
            results = response.json().get('results', [])
            for item in results:
                self.process_movie_detail(item['id'])
                time.sleep(0.05)
            self.stdout.write(self.style.SUCCESS(f'Page {page} processed successfully.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error on page {page}: {e}'))

    def process_movie_detail(self, movie_id):
        if movie_id in self.processed_movie_ids:
            return

        # Fetch data for all languages; primary language drives the main fields
        data_by_lang = {}
        for lang in self.LANGUAGES:
            data_by_lang[lang] = self.fetch_movie_detail(movie_id, lang)
            time.sleep(0.05)

        primary_lang = self.LANGUAGES[0]
        m = data_by_lang[primary_lang]

        if 'title' not in m:
            return

        genre_ids = self.get_or_create_genres(m.get('genres', []), data_by_lang)
        platform_ids = self.get_or_create_platforms(m.get('watch/providers', {}))
        dir_ids, act_ids = self.get_or_create_persons(m.get('credits', {}))

        cover_path = self.download_image(m.get('poster_path'), self.MOVIE_SUBDIR)

        movie_pk = self.pks['movie']

        self.fixtures['movies'].append(
            {
                'model': 'movies.movie',
                'pk': movie_pk,
                'fields': {
                    'title': m['title'],
                    'slug': f'{m["id"]}-{slugify(m["title"], allow_unicode=True)}'[:100],
                    'synopsis': m['overview'],
                    'release_date': m.get('release_date') or '2000-01-01',
                    'cover': cover_path,
                    'directors': dir_ids,
                    'actors': act_ids,
                    'genres': genre_ids,
                    'platforms': platform_ids,
                    'created_at': self.now,
                    'updated_at': self.now,
                },
            }
        )

        # Create a MovieTranslation record for every language
        for lang in self.LANGUAGES:
            lang_data = data_by_lang.get(lang, {})
            title_translated = lang_data.get('title') or m['title']
            synopsis_translated = lang_data.get('overview') or m['overview']

            # TMDB returns a language-specific poster_path when queried with that language
            translated_poster_path = lang_data.get('poster_path')
            translated_cover = self.download_image(
                translated_poster_path, self.MOVIE_TRANSLATION_SUBDIR
            )

            self.fixtures['movie_translations'].append(
                {
                    'model': 'movies.movietranslation',
                    'pk': self.pks['movie_translation'],
                    'fields': {
                        'movie': movie_pk,
                        'language': lang,
                        'title': title_translated,
                        'synopsis': synopsis_translated,
                        'image': translated_cover,
                    },
                }
            )
            self.pks['movie_translation'] += 1

        self.processed_movie_ids.add(movie_id)
        self.pks['movie'] += 1
        self.stdout.write(self.style.SUCCESS(f'Movie "{m["title"]}" processed.'))

    def get_or_create_genres(self, genres_data, data_by_lang):
        """
        Create Genre fixtures from the primary language data,
        then add GenreTranslation fixtures for every language.

        TMDB genre IDs are stable across languages, so we match translations
        by TMDB genre ID.
        """
        primary_lang = self.LANGUAGES[0]
        ids = []

        for g in genres_data:
            name = g['name']  # primary language name
            tmdb_genre_id = g['id']  # stable TMDB id used to match translations

            if name not in self.pks['genre']:
                pk = len(self.pks['genre']) + 1
                self.pks['genre'][name] = pk
                self.fixtures['genres'].append(
                    {
                        'model': 'genres.genre',
                        'pk': pk,
                        'fields': {
                            'name': name,
                            'slug': slugify(name),
                            'created_at': self.now,
                            'updated_at': self.now,
                        },
                    }
                )

                # Add a GenreTranslation for each language
                for lang in self.LANGUAGES:
                    lang_genres = (
                        data_by_lang.get(lang, {}).get('genres', [])
                        if lang != primary_lang
                        else genres_data
                    )
                    # Find the matching genre by TMDB id
                    translated_name = next(
                        (lg['name'] for lg in lang_genres if lg['id'] == tmdb_genre_id),
                        name,  # fall back to primary name if not found
                    )
                    self.fixtures['genre_translations'].append(
                        {
                            'model': 'genres.genretranslation',
                            'pk': self.pks['genre_translation'],
                            'fields': {
                                'genre': pk,
                                'language': lang,
                                'name': translated_name,
                            },
                        }
                    )
                    self.pks['genre_translation'] += 1

            ids.append(self.pks['genre'][name])
        return list(set(ids))

    def get_or_create_platforms(self, providers_data):
        ids = []
        flatrate = providers_data.get('results', {}).get('ES', {}).get('flatrate', [])
        for p in flatrate:
            name = p['provider_name']
            if name not in self.pks['platform']:
                pk = len(self.pks['platform']) + 1
                self.pks['platform'][name] = pk
                self.fixtures['platforms'].append(
                    {
                        'model': 'platforms.platform',
                        'pk': pk,
                        'fields': {
                            'name': name,
                            'slug': slugify(name),
                            'created_at': self.now,
                            'updated_at': self.now,
                        },
                    }
                )
            ids.append(self.pks['platform'][name])
        return list(set(ids))

    def get_or_create_persons(self, credits):
        dir_ids, act_ids = [], []
        crew = credits.get('crew', [])
        cast = credits.get('cast', [])
        people = [(p, 'dir') for p in crew if p['job'] == 'Director'] + [
            (p, 'act') for p in cast[:5]
        ]

        for p_data, p_type in people:
            name = p_data['name']
            if name not in self.pks['person']:
                pk = len(self.pks['person']) + 1
                self.pks['person'][name] = pk
                photo = self.download_image(p_data.get('profile_path'), self.PERSON_SUBDIR)
                self.fixtures['persons'].append(
                    {
                        'model': 'persons.person',
                        'pk': pk,
                        'fields': {
                            'name': name,
                            'slug': slugify(name, allow_unicode=True) + f'-{pk}',
                            'image': photo,
                            'created_at': self.now,
                            'updated_at': self.now,
                        },
                    }
                )

            if p_type == 'dir':
                dir_ids.append(self.pks['person'][name])
            else:
                act_ids.append(self.pks['person'][name])

        return list(set(dir_ids)), list(set(act_ids))
