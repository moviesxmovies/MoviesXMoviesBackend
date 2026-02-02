from django.db import models
from shared.models import Timestamps

class MovieList(Timestamps):
    """
    Model representing a list of movies created by a user.
    
    Attributes:
        name (models.CharField): The name of the movie list.
        description (models.TextField): A brief description of the movie list.
        user (models.ForeignKey): The user who created the movie list.
        movies (models.ManyToManyField): The movies included in the movie list.
    """
    class Privacity(models.TextChoices):
        """
        Enumeration for the privacy settings of the movie list.
        1. PUBLIC: The movie list is visible to everyone.
        2. FOLLOWERS: The movie list is visible to the creator's followers.
        3. PRIVATE: The movie list is only visible to the creator.
        """
        PUBLIC = 'P', 'Public'
        FOLLOWERS = 'F', 'Followers'
        PRIVATE = 'R', 'Private'
        
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    privacity = models.CharField(
        max_length=1,
        choices=Privacity.choices,
        default=Privacity.PUBLIC
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='movie_lists'
    )
    movies = models.ManyToManyField(
        'movies.Movie', 
        related_name='in_movie_lists', 
        blank=True
    )
    
    def __str__(self):
        return self.slug
