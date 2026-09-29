from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from .forms import CommentForm, PostForm, ProfileForm, RegistrationForm
from .models import Category, Comment, Post

POSTS_PER_PAGE = 10

User = get_user_model()


class AuthorRequiredMixin:
    """Пускает к редактированию и удалению только автора объекта.

    Остальных пользователей возвращает на страницу публикации.
    Подключается после LoginRequiredMixin, чтобы анонимов сначала
    отправляло на страницу входа.
    """

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)


class PostListMixin:
    model = Post
    paginate_by = POSTS_PER_PAGE


class IndexView(PostListMixin, ListView):
    template_name = 'blog/index.html'

    def get_queryset(self):
        return (
            Post.objects.published()
            .with_relations()
            .with_comment_count()
        )


class CategoryPostsView(PostListMixin, ListView):
    template_name = 'blog/category.html'

    def get_queryset(self):
        self.category = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True,
        )
        return (
            self.category.posts.published()
            .with_relations()
            .with_comment_count()
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(category=self.category, **kwargs)


class ProfileView(PostListMixin, ListView):
    template_name = 'blog/profile.html'

    def get_queryset(self):
        self.profile = get_object_or_404(
            User, username=self.kwargs['username']
        )
        return (
            self.profile.posts.visible_to(self.request.user)
            .with_relations()
            .with_comment_count()
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(profile=self.profile, **kwargs)


class ProfileEditView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse('blog:profile', args=(self.request.user.username,))


class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('blog:index')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        return Post.objects.visible_to(self.request.user).with_relations()

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            form=CommentForm(),
            comments=self.object.comments.select_related('author'),
            **kwargs,
        )


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    initial = {'pub_date': timezone.now}

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', args=(self.request.user.username,))


class PostChangeMixin(LoginRequiredMixin, AuthorRequiredMixin):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'


class PostEditView(PostChangeMixin, UpdateView):
    form_class = PostForm

    def get_success_url(self):
        return reverse('blog:post_detail', args=(self.object.pk,))


class PostDeleteView(PostChangeMixin, DeleteView):

    def get_context_data(self, **kwargs):
        # Шаблон create.html показывает удаляемый пост через form.instance.
        return super().get_context_data(
            form=PostForm(instance=self.object), **kwargs
        )

    def get_success_url(self):
        return reverse('blog:profile', args=(self.request.user.username,))


@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(
        Post.objects.visible_to(request.user), pk=post_id
    )
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


class CommentChangeMixin(LoginRequiredMixin, AuthorRequiredMixin):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs['post_id'])

    def get_success_url(self):
        return reverse('blog:post_detail', args=(self.kwargs['post_id'],))


class CommentEditView(CommentChangeMixin, UpdateView):
    form_class = CommentForm


class CommentDeleteView(CommentChangeMixin, DeleteView):
    pass
