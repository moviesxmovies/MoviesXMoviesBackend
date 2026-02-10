import json
import os
import time
from datetime import datetime

import requests
from prettyconf import config

now = datetime.now().isoformat()


class TMDBToFixture:
    BASE_URL = 'https://api.themoviedb.org/3'
    MEDIA_ROOT = 'media'
    MOVIE_SUBDIR = 'movies/covers'
    PERSON_SUBDIR = 'person/'

    def __init__(self, api_key):
        self.headers = {'Authorization': f'Bearer {api_key}'}
        self.movie_pk = 1
        self.person_pks = {}
        self.genre_pks = {}
        self.platform_pks = {}

        for subdir in [self.MOVIE_SUBDIR, self.PERSON_SUBDIR]:
            path = os.path.join(self.MEDIA_ROOT, subdir)
            if not os.path.exists(path):
                os.makedirs(path)

    def download_image(self, path, subdir):
        """
        Downloads an image from TMDB and saves it locally.
        subdir: self.MOVIE_SUBDIR or self.PERSON_SUBDIR
        """
        if not path:
            return f'{subdir}/no-image.png'

        filename = path.lstrip('/')
        full_local_path = os.path.join(self.MEDIA_ROOT, subdir, filename)
        db_relative_path = f'{subdir}/{filename}'

        if not os.path.exists(full_local_path):
            img_url = f'https://image.tmdb.org/t/p/w500/{path}'
            try:
                response = requests.get(img_url, stream=True)
                if response.status_code == 200:
                    with open(full_local_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                else:
                    return f'{subdir}/no-image.png'
            except Exception as e:
                print(f'Error descargando {img_url}: {e}')
                return f'{subdir}/no-image.png'

        return db_relative_path

    def get_mass_fixtures(self, pages=5):
        fixtures = []
        persons_fixtures = []
        genres_fixtures = []
        platforms_fixtures = []

        for page in range(1, pages + 1):
            url = f'{self.BASE_URL}/movie/popular?language=es-ES&page={page}'
            try:
                list_res = requests.get(url, headers=self.headers).json()
                results = list_res.get('results', [])
            except Exception:
                continue

            print(f'\n--- Page {page} ---')

            for item in results:
                d_url = f'{self.BASE_URL}/movie/{item["id"]}?append_to_response=credits,watch/providers&language=es-ES'
                m = requests.get(d_url, headers=self.headers).json()

                if 'title' not in m:
                    continue

                # --- Movie Image ---
                movie_cover = self.download_image(m.get('poster_path'), self.MOVIE_SUBDIR)

                # --- Genres ---
                current_movie_genres = []
                for g in m.get('genres', []):
                    name = g['name']
                    if name not in self.genre_pks:
                        self.genre_pks[name] = len(self.genre_pks) + 1
                        genres_fixtures.append(
                            {
                                'model': 'genres.genre',
                                'pk': self.genre_pks[name],
                                'fields': {
                                    'name': name,
                                    'slug': name.lower().replace(' ', '-'),
                                    'created_at': now,
                                    'updated_at': now,
                                },
                            }
                        )
                    current_movie_genres.append(self.genre_pks[name])

                # --- Platforms ---
                current_movie_platforms = []
                providers = (
                    m.get('watch/providers', {})
                    .get('results', {})
                    .get('ES', {})
                    .get('flatrate', [])
                )
                for p in providers:
                    name = p['provider_name']
                    if name not in self.platform_pks:
                        self.platform_pks[name] = len(self.platform_pks) + 1
                        platforms_fixtures.append(
                            {
                                'model': 'platforms.platform',
                                'pk': self.platform_pks[name],
                                'fields': {
                                    'name': name,
                                    'slug': name.lower().replace(' ', '-'),
                                    'created_at': now,
                                    'updated_at': now,
                                },
                            }
                        )
                    current_movie_platforms.append(self.platform_pks[name])

                # --- Persons (Directors and Actors) ---
                current_movie_directors = []
                current_movie_actors = []

                # Combine cast and crew to process photos
                crew = m.get('credits', {}).get('crew', [])
                cast = m.get('credits', {}).get('cast', [])

                # Format: (name, type, profile_path)
                people = [
                    (p['name'], 'dir', p.get('profile_path'))
                    for p in crew
                    if p['job'] == 'Director'
                ] + [(p['name'], 'act', p.get('profile_path')) for p in cast[:5]]

                for p_name, p_type, p_path in people:
                    if p_name not in self.person_pks:
                        self.person_pks[p_name] = len(self.person_pks) + 1
                        person_photo = self.download_image(p_path, self.PERSON_SUBDIR)

                        persons_fixtures.append(
                            {
                                'model': 'persons.person',
                                'pk': self.person_pks[p_name],
                                'fields': {
                                    'name': p_name,
                                    'slug': p_name.lower().replace(' ', '-'),
                                    'image': person_photo,
                                    'created_at': now,
                                    'updated_at': now,
                                },
                            }
                        )

                    if p_type == 'dir':
                        current_movie_directors.append(self.person_pks[p_name])
                    else:
                        current_movie_actors.append(self.person_pks[p_name])

                # --- Movie ---
                fixtures.append(
                    {
                        'model': 'movies.movie',
                        'pk': self.movie_pk,
                        'fields': {
                            'title': m['title'],
                            'slug': f'{m["id"]}-{m["title"].lower().replace(" ", "-")}'[:100],
                            'synopsis': m['overview'],
                            'release_date': m.get('release_date') or '2000-01-01',
                            'cover': movie_cover,
                            'directors': list(set(current_movie_directors)),
                            'actors': list(set(current_movie_actors)),
                            'genres': list(set(current_movie_genres)),
                            'platforms': list(set(current_movie_platforms)),
                            'created_at': now,
                            'updated_at': now,
                        },
                    }
                )
                self.movie_pk += 1
                print(f'Processed: {m["title"]}')
                time.sleep(0.05)

        return genres_fixtures + persons_fixtures + platforms_fixtures + fixtures


# Execution
TOKEN = config('TMDB_API_KEY')
converter = TMDBToFixture(TOKEN)
final_json = converter.get_mass_fixtures(pages=200)

with open('movie_fixtures.json', 'w', encoding='utf-8') as f:
    json.dump(final_json, f, indent=4, ensure_ascii=False)
