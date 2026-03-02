from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Count, Q


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.

    Attributes:
        bio (models.TextField): A brief biography of the user.
        boarded (models.BooleanField): Indicates if the user has completed onboarding.
        verified (models.BooleanField): Indicates if the user's email is verified.
        email (models.EmailField): The user's email address, must be unique.
        picture (models.ImageField): The user's profile picture, with a default image.
        following_person (models.ManyToManyField): A many-to-many relationship to Person model for following people.
        following (models.ManyToManyField): A many-to-many relationship to other Users for following users.
        platforms (models.ManyToManyField): A many-to-many relationship to Platform model for platforms the user is associated with.
        verification_code (models.CharField): A code used for email verification, can be null or blank.
    """

    bio = models.TextField(blank=True, null=True)
    boarded = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    picture = models.ImageField(upload_to='users', default='users/default.png')
    following_person = models.ManyToManyField(
        'persons.Person', related_name='followers', blank=True
    )
    following = models.ManyToManyField('users.User', related_name='followers', blank=True)
    platforms = models.ManyToManyField('platforms.Platform', related_name='users', blank=True)
    verification_code = models.CharField(max_length=6, null=True, blank=True)

    def is_following(self, check_user):
        """Check if user is following check_user

        Args:
            check_user (User): The user to check with

        Returns:
            Boolean: If self is following check_user
        """
        return self.following.filter(pk=check_user.pk).exists()

    def is_followed_by(self, check_user):
        """Check if user is being followed by check_user

        Args:
            check_user (User): The user to check with

        Returns:
            Boolean: If self is being followed by check_user
        """
        return self.followers.filter(pk=check_user.pk).exists()

    def is_friend(self, check_user):
        """Checks if users are friends (mutual following)

        Args:
            check_user (User): The user to check with

        Returns:
            Boolean: If they are friends or not
        """
        if not check_user or self.pk == check_user.pk:
            return False

        return self.is_following(check_user) and self.is_followed_by(check_user)

    @property
    def friends(self):
        """Get all friends (mutual following) of the user

        Returns:
            QuerySet: A queryset of users who are friends with the user
        """
        return self.following.filter(followers=self)

    def suggest_friends(self):
        """
        Suggest friends based on users followed by people you follow (friends-of-friends).

        The suggestions are users who are followed by your `following` set, excluding
        yourself and users you already follow, ordered by how many of your followings
        also follow them.

        Returns:
            models.QuerySet: A queryset of suggested users.
        """
        following_ids = self.following.values_list('id', flat=True)

        return (
            User.objects.filter(followers__in=following_ids)
            .exclude(Q(id=self.id) | Q(id__in=following_ids))
            .annotate(
                common_friends_count=Count('followers', filter=Q(followers__in=following_ids))
            )
            .order_by('-common_friends_count', 'id')
            .distinct()
        )

    def follow(self, other_user):
        """Follow another user

        Args:
            other_user (User): The user to follow
        """
        if other_user and other_user != self:
            self.following.add(other_user)

    def unfollow(self, other_user):
        """Unfollow another user

        Args:
            other_user (User): The user to unfollow
        """
        if other_user and other_user != self:
            self.following.remove(other_user)
