from django.db import models
from shared.models import Timestamps

class Award(Timestamps):
    class Category(models.TextChoices):
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
    category = models.CharField(choices=Category, blank=True)
    icon = models.ImageField(upload_to='awards', default='awards/no-award.png')
    date = models.DateField(blank=True, null=True)