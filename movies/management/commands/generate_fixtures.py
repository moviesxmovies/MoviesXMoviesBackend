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
    PLATFORM_SUBDIR = 'platforms'

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
        self.processed_genre_ids = set()
        self.processed_person_ids = set()
        self.processed_platform_ids = set()

        self.lang_index = {lang: i for i, lang in enumerate(self.LANGUAGES)}

        self.fixtures = {
            'genres': [],
            'genre_translations': [],
            'persons': [],
            'platforms': [],
            'movies': [],
            'movie_translations': [],
            'person_translations': [],
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
            + self.fixtures['person_translations']
        )

        with open(options['output'], 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(
                f'Extraction completed: {len(self.fixtures["movies"])} movies, {len(self.fixtures["genres"])} genres, {len(self.fixtures["platforms"])} platforms, {len(self.fixtures["persons"])} persons.'
            )
        )

    def setup_directories(self):
        for subdir in [
            self.MOVIE_SUBDIR,
            self.MOVIE_TRANSLATION_SUBDIR,
            self.PERSON_SUBDIR,
            self.PLATFORM_SUBDIR,
        ]:
            os.makedirs(os.path.join(self.MEDIA_ROOT, subdir), exist_ok=True)

    def download_image(self, path, subdir):
        if not path:
            return f'{subdir}/default.png'

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
                return f'{subdir}/default.png'
        return db_path

    def fetch_movie_detail(self, movie_id, language):
        url = (
            f'{self.BASE_URL}/movie/{movie_id}'
            f'?append_to_response=credits,watch/providers&language={language}-{language.upper()}'
        )
        return requests.get(url, headers=self.headers).json()

    def process_page(self, page):
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

        movie_pk = m['id']

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

        for lang in self.LANGUAGES:
            lang_data = data_by_lang.get(lang, {})
            title_translated = lang_data.get('title') or m['title']
            synopsis_translated = lang_data.get('overview') or m['overview']
            translated_cover = self.download_image(
                lang_data.get('poster_path'), self.MOVIE_TRANSLATION_SUBDIR
            )

            translation_pk = movie_pk * 100 + self.lang_index[lang]

            self.fixtures['movie_translations'].append(
                {
                    'model': 'movies.movietranslation',
                    'pk': translation_pk,
                    'fields': {
                        'movie': movie_pk,
                        'language': lang,
                        'title': title_translated,
                        'synopsis': synopsis_translated,
                        'image': translated_cover,
                        'created_at': self.now,
                        'updated_at': self.now,
                    },
                }
            )

        self.processed_movie_ids.add(movie_id)
        self.stdout.write(self.style.SUCCESS(f'Movie "{m["title"]}" processed.'))

    def get_or_create_genres(self, genres_data, data_by_lang):
        primary_lang = self.LANGUAGES[0]
        ids = []

        for g in genres_data:
            tmdb_genre_id = g['id']
            name = g['name']

            if tmdb_genre_id not in self.processed_genre_ids:
                self.processed_genre_ids.add(tmdb_genre_id)
                self.fixtures['genres'].append(
                    {
                        'model': 'genres.genre',
                        'pk': tmdb_genre_id,
                        'fields': {
                            'name': name,
                            'slug': slugify(name),
                            'created_at': self.now,
                            'updated_at': self.now,
                        },
                    }
                )

                for lang in self.LANGUAGES:
                    lang_genres = (
                        genres_data
                        if lang == primary_lang
                        else data_by_lang.get(lang, {}).get('genres', [])
                    )
                    translated_name = next(
                        (lg['name'] for lg in lang_genres if lg['id'] == tmdb_genre_id),
                        name,
                    )
                    translation_pk = tmdb_genre_id * 100 + self.lang_index[lang]
                    self.fixtures['genre_translations'].append(
                        {
                            'model': 'genres.genretranslation',
                            'pk': translation_pk,
                            'fields': {
                                'genre': tmdb_genre_id,
                                'language': lang,
                                'name': translated_name,
                                'created_at': self.now,
                                'updated_at': self.now,
                            },
                        }
                    )

            ids.append(tmdb_genre_id)
        return list(set(ids))

    def get_or_create_platforms(self, providers_data):
        ids = []
        flatrate = providers_data.get('results', {}).get('ES', {}).get('flatrate', [])
        for p in flatrate:
            provider_id = p['provider_id']
            name = p['provider_name']

            if provider_id not in self.processed_platform_ids:
                self.processed_platform_ids.add(provider_id)
                logo = self.download_image(p.get('logo_path'), self.PLATFORM_SUBDIR)
                self.fixtures['platforms'].append(
                    {
                        'model': 'platforms.platform',
                        'pk': provider_id,
                        'fields': {
                            'name': name,
                            'slug': slugify(name),
                            'image': logo,
                            'created_at': self.now,
                            'updated_at': self.now,
                        },
                    }
                )
            ids.append(provider_id)
        return list(set(ids))

    def fetch_person_detail(self, person_id, language=None):
        url = f'{self.BASE_URL}/person/{person_id}'
        if language:
            url += f'?language={language}-{language.upper()}'
        return requests.get(url, headers=self.headers).json()

    def get_or_create_persons(self, credits):
        dir_ids, act_ids = [], []
        crew = credits.get('crew', [])
        cast = credits.get('cast', [])
        people = [(p, 'dir') for p in crew if p['job'] == 'Director'] + [
            (p, 'act') for p in cast[:5]
        ]

        for p_data, p_type in people:
            person_id = p_data['id']
            name = p_data['name']

            if person_id not in self.processed_person_ids:
                self.processed_person_ids.add(person_id)

                detail = self.fetch_person_detail(person_id)
                time.sleep(0.05)

                photo = self.download_image(p_data.get('profile_path'), self.PERSON_SUBDIR)
                self.fixtures['persons'].append(
                    {
                        'model': 'persons.person',
                        'pk': person_id,
                        'fields': {
                            'name': name,
                            'slug': slugify(name, allow_unicode=True) + f'-{person_id}',
                            'image': photo,
                            'gender': detail.get('gender', 0),
                            'biography': detail.get('biography') or '',
                            'birthday': detail.get('birthday'),
                            'deathday': detail.get('deathday'),
                            'created_at': self.now,
                            'updated_at': self.now,
                        },
                    }
                )

                for lang in self.LANGUAGES:
                    lang_detail = self.fetch_person_detail(person_id, lang)
                    time.sleep(0.05)

                    translation_pk = person_id * 100 + self.lang_index[lang]
                    self.fixtures['person_translations'].append(
                        {
                            'model': 'persons.persontranslation',
                            'pk': translation_pk,
                            'fields': {
                                'person': person_id,
                                'language': lang,
                                'biography': lang_detail.get('biography') or '',
                                'created_at': self.now,
                                'updated_at': self.now,
                            },
                        }
                    )

            if p_type == 'dir':
                dir_ids.append(person_id)
            else:
                act_ids.append(person_id)

        return list(set(dir_ids)), list(set(act_ids))
