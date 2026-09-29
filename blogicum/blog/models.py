from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

User = get_user_model()

MAX_TITLE_LENGTH = 256
STR_PREVIEW_LENGTH = 30


class PostQuerySet(models.QuerySet):
    """Выборки публикаций, которые нужны на страницах блога."""

    @staticmethod
    def _is_published():
        return Q(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now(),
        )

    def with_relations(self):
        return self.select_related('author', 'category', 'location')

    def published(self):
        """Посты, которые видны всем посетителям сайта."""
        return self.filter(self._is_published())

    def visible_to(self, user):
        """Опубликованные посты плюс все посты самого пользователя.

        Автор видит свои отложенные и снятые с публикации записи,
        остальные посетители - только опубликованные.
        """
        condition = self._is_published()
        if user.is_authenticated:
            condition |= Q(author=user)
        return self.filter(condition)

    def with_comment_count(self):
        # В запросах с агрегацией Django не применяет Meta.ordering,
        # поэтому порядок сортировки задаём явно.
        return self.annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')


class PublishedModel(models.Model):
    """Абстрактная модель с флагом публикации и датой создания."""

    is_published = models.BooleanField(
        'Опубликовано',
        default=True,
        help_text='Снимите галочку, чтобы скрыть публикацию.',
    )
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        abstract = True


class Category(PublishedModel):
    title = models.CharField('Заголовок', max_length=MAX_TITLE_LENGTH)
    description = models.TextField('Описание')
    slug = models.SlugField(
        'Идентификатор',
        unique=True,
        help_text=(
            'Идентификатор страницы для URL; разрешены символы латиницы, '
            'цифры, дефис и подчёркивание.'
        ),
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.title[:STR_PREVIEW_LENGTH]


class Location(PublishedModel):
    name = models.CharField('Название места', max_length=MAX_TITLE_LENGTH)

    class Meta:
        verbose_name = 'местоположение'
        verbose_name_plural = 'Местоположения'

    def __str__(self):
        return self.name[:STR_PREVIEW_LENGTH]


class Post(PublishedModel):
    title = models.CharField('Заголовок', max_length=MAX_TITLE_LENGTH)
    text = models.TextField('Текст')
    pub_date = models.DateTimeField(
        'Дата и время публикации',
        help_text=(
            'Если установить дату и время в будущем — '
            'можно делать отложенные публикации.'
        ),
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор публикации',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Местоположение',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Категория',
    )
    image = models.ImageField(
        'Изображение',
        upload_to='post_images/',
        blank=True,
    )

    objects = PostQuerySet.as_manager()

    class Meta:
        verbose_name = 'публикация'
        verbose_name_plural = 'Публикации'
        ordering = ('-pub_date',)
        default_related_name = 'posts'

    def __str__(self):
        return self.title[:STR_PREVIEW_LENGTH]


class Comment(models.Model):
    text = models.TextField('Текст комментария')
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name='Публикация',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор комментария',
    )
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        verbose_name = 'комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('created_at',)
        default_related_name = 'comments'

    def __str__(self):
        return f'{self.author}: {self.text[:STR_PREVIEW_LENGTH]}'
