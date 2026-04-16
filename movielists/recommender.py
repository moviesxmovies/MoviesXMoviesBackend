import logging
import pickle

from django.core.cache import cache

logger = logging.getLogger(__name__)


class RecommenderModel:
    _data = None
    _version = None

    @classmethod
    def get_data(cls):
        current_version = cache.get('ml_model_version')

        if cls._data is None or cls._version != current_version:
            logger.info('Cache miss or version mismatch for ALS model. Loading from cache...')
            raw_data = cache.get('movie_recommendation_model')
            if raw_data:
                try:
                    cls._data = pickle.loads(raw_data)
                    cls._version = current_version
                    logger.info('Model loaded from cache.')
                except Exception as e:
                    logger.error(f'Error loading model: {e}')

        return cls._data

    @classmethod
    def invalidate(cls):
        cls._data = None
        cls._version = None
