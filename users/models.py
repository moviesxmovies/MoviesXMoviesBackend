import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Exists, IntegerField, OuterRef, Q
from django.utils.translation import gettext_lazy as _


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
        platforms (models.ManyToManyField): A many-to-many relationship to Platform model for platforms the user is associated with.
        verification_code (models.CharField): A code used for email verification, can be null or blank.
    """

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    bio = models.TextField(blank=True, null=True)
    boarded = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    picture = models.ImageField(upload_to='users', default='users/default.png')
    following_person = models.ManyToManyField(
        'persons.Person', related_name='followers', blank=True
    )
    platforms = models.ManyToManyField('platforms.Platform', related_name='users', blank=True)
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    forgot_password_code = models.CharField(max_length=6, null=True, blank=True)
    unseen_movies = models.ManyToManyField('movies.Movie', related_name='users_unseen', blank=True)
    preferred_language = models.CharField(max_length=2, default='en')
    friends = models.ManyToManyField('self', through='FriendShip', symmetrical=True, blank=True)

    def is_friend(self, check_user):
        """Checks if users are friends (mutual following)

        Args:
            check_user (User): The user to check with

        Returns:
            Boolean: If they are friends or not
        """
        if check_user is None or not check_user.is_authenticated or self.pk == check_user.pk:
            return False
        return FriendShip.objects.filter(
            Q(user1=self, user2=check_user) | Q(user1=check_user, user2=self)
        ).exists()

    def suggest_friends(self):
        """
        Suggest friends based on mutual friends, with a recency fallback.

        Strategy
        --------
        Everything runs as a single SQL round-trip using correlated
        subqueries — no Python-side list materialisation.

        1. `already_friend`     — Exists() subquery: candidate is already a friend.
        2. `active_request`     — Exists() subquery: non-rejected FriendRequest exists.
        3. `common_friends_count` — correlated COUNT: how many users are friends
           of both `self` and the candidate row, computed entirely in SQL.

        Ordering: mutual-friends desc → date_joined desc → id asc.
        This naturally degrades to a recency sort when common_friends_count = 0
        for everyone (new user, isolated graph), so no separate fallback branch
        or extra query is needed.

        Args:
            limit (int): Maximum number of suggestions to return. Defaults to 10.

        Returns:
            QuerySet[User]: Annotated with `common_friends_count`.
        """
        already_friend = FriendShip.objects.filter(
            Q(user1=self, user2=OuterRef('pk')) | Q(user1=OuterRef('pk'), user2=self)
        )

        active_request = FriendRequest.objects.filter(
            Q(from_user=self, to_user=OuterRef('pk')) | Q(from_user=OuterRef('pk'), to_user=self)
        ).exclude(status=FriendRequest.Status.REJECTED)

        ft = FriendShip._meta.db_table  # friendship table alias
        ut = User._meta.db_table  # user table alias

        # For each candidate row (ut.id = candidate), count users T such that:
        #   - T is a friend of `self`  (via f_mine)
        #   - T is a friend of candidate (via f_theirs)
        mutual_count_raw = models.expressions.RawSQL(
            f"""
        SELECT COUNT(*)
        FROM {ft} f_mine
        WHERE
            (f_mine.user1_id = %s OR f_mine.user2_id = %s)
            AND EXISTS (
                SELECT 1
                FROM {ft} f_theirs
                WHERE
                    f_theirs.user1_id = CASE
                        WHEN f_mine.user1_id = %s THEN f_mine.user2_id
                        ELSE f_mine.user1_id
                    END
                    AND f_theirs.user2_id = {ut}.id
                UNION ALL
                SELECT 1
                FROM {ft} f_theirs2
                WHERE
                    f_theirs2.user2_id = CASE
                        WHEN f_mine.user1_id = %s THEN f_mine.user2_id
                        ELSE f_mine.user1_id
                    END
                    AND f_theirs2.user1_id = {ut}.id
            )
        """,
            [self.pk, self.pk, self.pk, self.pk],
            output_field=IntegerField(),  # <--- OBLIGATORIO
        )
        suggestions = (
            User.objects.exclude(pk=self.pk)
            .annotate(
                _is_friend=Exists(already_friend),
                _active_request=Exists(active_request),
                common_friends_count=mutual_count_raw,
            )
            .filter(_is_friend=False, _active_request=False)
            .order_by('-common_friends_count', '-date_joined', 'id')
        )

        print(suggestions.query)  # Debug: print the generated SQL query

        return suggestions

    def get_friends(self):
        friend_ids = (
            FriendShip.objects.filter(Q(user1=self) | Q(user2=self))
            .annotate(
                friend_id=models.Case(
                    models.When(user1=self, then=models.F('user2')),
                    default=models.F('user1'),
                    output_field=models.IntegerField(),
                )
            )
            .values('friend_id')
        )
        return User.objects.filter(id__in=friend_ids)

    def get_friend_request_status(self, check_user):
        if check_user is None or self.pk == check_user.pk:
            return None
        try:
            friend_request = FriendRequest.objects.get(
                Q(from_user=self, to_user=check_user) | Q(from_user=check_user, to_user=self)
            )
            return friend_request.status
        except FriendRequest.DoesNotExist:
            return None


class FriendRequest(models.Model):
    """
    Model representing a friend request between users.

    Attributes:
        from_user (models.ForeignKey): The user who sent the friend request.
        to_user (models.ForeignKey): The user who received the friend request.
        created_at (models.DateTimeField): The timestamp when the friend request was created.
    """

    class Status(models.TextChoices):
        PENDING = 'P', _('Pending')
        ACCEPTED = 'A', _('Accepted')
        REJECTED = 'R', _('Rejected')

    from_user = models.ForeignKey(
        User, related_name='sent_friend_requests', on_delete=models.CASCADE
    )
    to_user = models.ForeignKey(
        User, related_name='received_friend_requests', on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.PENDING)

    class Meta:
        unique_together = ('from_user', 'to_user')
        verbose_name = _('Friend Request')
        verbose_name_plural = _('Friend Requests')

    def __str__(self):
        return f'FriendRequest from {self.from_user.username} to {self.to_user.username}'

    def accept(self):
        """Accept the friend request, creating a FriendShip record."""
        if self.status != self.Status.PENDING:
            raise ValueError(_('Only pending friend requests can be accepted.'))
        FriendShip.objects.create(user1=self.from_user, user2=self.to_user)
        self.status = self.Status.ACCEPTED
        self.save()

    def reject(self):
        """Reject the friend request."""
        if self.status != self.Status.PENDING:
            raise ValueError(_('Only pending friend requests can be rejected.'))
        self.status = self.Status.REJECTED
        self.save()

    def reset(self):
        """Reset a rejected/accepted friend request back to pending."""
        self.status = self.Status.PENDING
        self.created_at = datetime.datetime.now()
        self.save(update_fields=['status', 'created_at'])


class FriendShip(models.Model):
    """
    Model representing a friendship between two users.

    Attributes:
        user1 (models.ForeignKey): One user in the friendship.
        user2 (models.ForeignKey): The other user in the friendship.
        created_at (models.DateTimeField): The timestamp when the friendship was created.
    """

    user1 = models.ForeignKey(User, related_name='friendship_user1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='friendship_user2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')
        verbose_name = _('Friendship')
        verbose_name_plural = _('Friendships')
        indexes = [
            models.Index(fields=['user2', 'user1'], name='friendship_user2_user1_idx'),
        ]

    def __str__(self):
        return f'FriendShip(user1={self.user1.username}, user2={self.user2.username})'
