from django.db import models
from shared.models import Timestamps

class Award(Timestamps):
    """
    An award or nomination given in recognition of excellence in cinematic achievements.
    Attributes:
        name (models.CharField): The name of the award.
        slug (models.CharField): A URL-friendly version of the award's name.
        category (models.CharField): The category of the award.
        icon (models.ImageField): An icon representing the award.
        date (models.DateField): The date when the award was given.
    """
    class Category(models.TextChoices):
        """
        Enumeration of award categories.
        """
        # MOVIES
        BEST_PICTURE = 'BP', 'Best Picture'
        BEST_ANIMATED_FEATURE = 'BA', 'Best Animated Feature'
        BEST_DOCUMENTARY = 'BD', 'Best Documentary'
        BEST_INTERNATIONAL_FEATURE = 'IF', 'Best International Feature'
        
        # ACTORS
        BEST_ACTOR = 'MA', 'Best Actor in a Leading Role'
        BEST_ACTRESS = 'WA', 'Best Actress in a Leading Role'
        BEST_SUPPORTING_ACTOR = 'SA', 'Best Supporting Actor'
        BEST_SUPPORTING_ACTRESS = 'SX', 'Best Supporting Actress'
        
        # DIRECTING
        BEST_DIRECTOR = 'DR', 'Best Director'
        BEST_DEBUT_DIRECTOR = 'DD', 'Best Debut Director'
        
    name = models.CharField(max_length=32, unique=True)
    slug = models.CharField(max_length=32, unique=True)
    category = models.CharField(choices=Category, blank=True,max_length=2)
    icon = models.ImageField(upload_to='awards', default='awards/no-award.png')
    date = models.DateField(blank=True, null=True)