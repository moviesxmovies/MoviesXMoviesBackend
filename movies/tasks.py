import logging
import pickle

from django.core.cache import cache
from django_rq import job
from implicit.als import AlternatingLeastSquares
from scipy.sparse import csr_matrix

from movies.models import Movie
from ratings.models import Rating
from users.models import User

logger = logging.getLogger(__name__)


@job
def retrain_professional_model() -> str:
    """Retrain the ALS recommendation model and store it in the cache.

    Fetches all user-item ratings from the database, builds a sparse
    item-user interaction matrix, trains an ALS model via the Implicit
    library, and serializes the resulting model and ID mappings into the
    Django cache under the key ``'movie_recommendation_model'``.

    The cached payload is a ``pickle``-serialized dict with the keys:

    - ``model``: the fitted ``AlternatingLeastSquares`` instance.
    - ``user_id_map``: mapping from original user PKs to contiguous indices.
    - ``movie_id_map``: mapping from original movie PKs to contiguous indices.
    - ``reverse_movie_map``: inverse of ``movie_id_map``.
    - ``user_items_matrix``: transposed user-item ``csr_matrix``.

    Returns:
        str: ``'No ratings to train the model'`` if no ratings exist,
        otherwise ``'Model Implicit (ALS) trained'``.
    """
    ratings_qs = Rating.objects.values_list('user_id', 'movie_id', 'rating')
    if not ratings_qs.exists():
        logger.info('No ratings to traind the model')
        return 'No ratings to train the model'

    users_list = list(User.objects.values_list('id', flat=True))
    movies_list = list(Movie.objects.values_list('id', flat=True))

    user_id_map = {old_id: new_id for new_id, old_id in enumerate(users_list)}
    movie_id_map = {old_id: new_id for new_id, old_id in enumerate(movies_list)}
    reverse_movie_map = {new_id: old_id for old_id, new_id in movie_id_map.items()}

    rows, cols, data = [], [], []
    for u_id, m_id, rating in ratings_qs:
        if u_id in user_id_map and m_id in movie_id_map:
            rows.append(movie_id_map[m_id])
            cols.append(user_id_map[u_id])
            data.append(float(rating))

    item_user_matrix = csr_matrix((data, (rows, cols)), shape=(len(movies_list), len(users_list)))

    model = AlternatingLeastSquares(
        factors=100, regularization=0.05, iterations=20, calculate_training_loss=True
    )
    model.fit(item_user_matrix)

    trained_data = {
        'model': model,
        'user_id_map': user_id_map,
        'movie_id_map': movie_id_map,
        'reverse_movie_map': reverse_movie_map,
        'user_items_matrix': item_user_matrix.T.tocsr(),
    }
    cache.set(
        'movie_recommendation_model',
        pickle.dumps(trained_data),
        timeout=None,
    )
    logger.info(
        f'Successfully trained model for {len(users_list)} users and {len(movies_list)} movies relating by {len(ratings_qs)} ratings'
    )
    return 'Model Implicit (ALS) trained'
