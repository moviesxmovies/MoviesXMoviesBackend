import pickle
from lightfm import LightFM
import logging
from lightfm.data import Dataset
from scipy.sparse import csr_matrix
from django.core.cache import cache
from django_rq import job
from ratings.models import Rating
from movies.models import Movie
from users.models import User
from genres.models import Genre
from platforms.models import Platform
from persons.models import Person

logger = logging.getLogger(__name__)

@job
def retrain_professional_model() -> str:
    ratings_qs = list(Rating.objects.values_list('user_id', 'movie_id', 'rating'))
    if not ratings_qs:
        logger.info('No ratings found, skipping model training')
        return 'No ratings to train the model'

    dataset = Dataset()

    all_user_ids = list(User.objects.values_list('id', flat=True))
    all_movie_ids = list(Movie.objects.values_list('id', flat=True))

    genre_features    = [f'genre:{s}'    for s in Genre.objects.values_list('slug', flat=True)]
    platform_features = [f'platform:{s}' for s in Platform.objects.values_list('slug', flat=True)]
    person_features   = [f'person:{s}'   for s in Person.objects.values_list('slug', flat=True)]
    user_plat_features = [f'user_platform:{s}' for s in Platform.objects.values_list('slug', flat=True)]

    dataset.fit(
        users=all_user_ids,
        items=all_movie_ids,
        item_features=genre_features + platform_features + person_features,
        user_features=user_plat_features,
    )

    interactions, weights = dataset.build_interactions(
        (uid, mid, float(r)) for uid, mid, r in ratings_qs
    )

    item_features = dataset.build_item_features(
        (
            movie.id,
            [f'genre:{g.slug}'    for g in movie.genres.all()]
            + [f'platform:{p.slug}' for p in movie.platforms.all()]
            + [f'person:{a.slug}'   for a in movie.actors.all()]
            + [f'person:{d.slug}'   for d in movie.directors.all()],
        )
        for movie in Movie.objects.prefetch_related('genres', 'platforms', 'actors', 'directors')
    )

    user_features = dataset.build_user_features(
        (user.id, [f'user_platform:{p.slug}' for p in user.platforms.all()])
        for user in User.objects.prefetch_related('platforms')
    )

    model = LightFM(
        no_components=64,
        loss='warp',
        learning_rate=0.05,
        item_alpha=1e-6,
        user_alpha=1e-6,
    )
    model.fit(
        interactions,
        item_features=item_features,
        user_features=user_features,
        sample_weight=weights,
        epochs=30,
        num_threads=4,
    )

    cache.set('movie_recommendation_model', pickle.dumps({
        'model': model,
        'dataset': dataset,
        'item_features': item_features,
        'user_features': user_features,
    }), timeout=None)

    logger.info('LightFM model trained and cached successfully')
    return 'LightFM model trained successfully'