import pickle
from scipy.sparse import csr_matrix
from django.core.cache import cache
from django_rq import job
from implicit.als import AlternatingLeastSquares

from ratings.models import Rating
from movies.models import Movie
from users.models import User


@job
def retrain_professional_model():
    ratings_qs = Rating.objects.values_list('user_id', 'movie_id', 'rating')

    if not ratings_qs.exists():
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
    return 'Modelo Implicit (ALS) entrenado exitosamente'
