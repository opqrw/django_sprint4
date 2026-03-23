from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, QuerySet
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic.edit import CreateView

from blog.models import Category, Comment, Post
from .forms import CommentForm, PostForm, UserEditForm


User = get_user_model()
POSTS_PER_PAGE = 10


class RegistrationView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/registration_form.html'


class ProfileUpdateView(LoginRequiredMixin, CreateView):
    form_class = UserEditForm
    template_name = 'blog/user.html'

    def get(self, request, *args, **kwargs):
        form = UserEditForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=request.user.username)
        return render(request, self.template_name, {'form': form})


def paginate_queryset(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_posts_queryset() -> QuerySet:
    return Post.objects.select_related(
        'author', 'category', 'location'
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def get_visible_posts_queryset() -> QuerySet:
    return get_posts_queryset().filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now(),
    )


def get_post_comments_queryset() -> QuerySet:
    return Comment.objects.select_related('author', 'post').order_by(
        'created_at'
    )


def get_post_detail_queryset(user) -> QuerySet:
    if user.is_authenticated:
        return (get_posts_queryset().filter(author=user)
                | get_visible_posts_queryset()).distinct()
    return get_visible_posts_queryset()


def get_profile_posts_queryset(profile, viewer) -> QuerySet:
    post_list = get_posts_queryset().filter(author=profile)
    if viewer != profile:
        post_list = post_list.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now(),
        )
    return post_list


def index(request):
    page_obj = paginate_queryset(request, get_visible_posts_queryset())
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def post_detail(request, post_id):
    post = get_object_or_404(get_post_detail_queryset(request.user), pk=post_id)
    context = {
        'post': post,
        'comments': get_post_comments_queryset().filter(post=post),
    }
    if request.user.is_authenticated:
        context['form'] = CommentForm()
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug, is_published=True)
    post_list = get_visible_posts_queryset().filter(category=category)
    page_obj = paginate_queryset(request, post_list)
    context = {
        'category': category,
        'page_obj': page_obj,
    }
    return render(request, 'blog/category.html', context)


def profile(request, username):
    profile = get_object_or_404(User, username=username)
    page_obj = paginate_queryset(
        request,
        get_profile_posts_queryset(profile, request.user),
    )
    context = {
        'profile': profile,
        'page_obj': page_obj,
    }
    return render(request, 'blog/profile.html', context)


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(get_posts_queryset(), pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(get_posts_queryset(), pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(get_post_detail_queryset(request.user), pk=post_id)
    if request.method != 'POST':
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        get_post_comments_queryset(),
        pk=comment_id,
        post_id=post_id,
    )
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'form': form, 'comment': comment})


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        get_post_comments_queryset(),
        pk=comment_id,
        post_id=post_id,
    )
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
