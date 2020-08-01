from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import *
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page

@cache_page(20, key_prefix="index_page")
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request,
        "index.html",
        {"page": page,
         "paginator": paginator,}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "group.html", {"group": group,
                                          "posts": posts,
                                          "page": page,
                                          "paginator": paginator})


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("index")
    return render(request, "new.html", {"form": form,
                                        "title_text": "Добавить запись",
                                        "button_text": "Добавить"})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post = author.posts.all()
    paginator = Paginator(post, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    following = Follow.objects.filter(author=author)
    return render(request, "profile.html", {"author": author,
                                            "count":paginator.count,
                                            "page": page,
                                            "post": post,
                                            "paginator": paginator,
                                            "following":following})


def post_view(request, username, post_id):
    """Просмотр одного поста."""
    post = get_object_or_404(Post, id=post_id, author__username=username)
    form = CommentForm(request.POST or None)
    author = post.author
    count = author.posts.count()
    return render(request, 'post.html', {
        'post': post,
        "author": author,
        'items': post.comments.all(),
        'form': form,
        "count": count
    })


@login_required
def post_edit(request, username, post_id):
    if request.user.username != username:
        return redirect("post", username=username, post_id=post_id)
    post = get_object_or_404(Post, author__username=username, id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect("post", username=username, post_id=post_id)
    return render(request, "new.html", {"form":form, "post":post,
                                        "title_text": "Редактировать запись",
                                        "button_text": "Сохранить"})

def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    """Добавление комментария к посту."""
    form = CommentForm(request.POST or None)
    if form.is_valid():
        form.instance.author = request.user
        form.instance.post_id = post_id
        form.save()
    return redirect('post', username=username, post_id=post_id)


@login_required
def follow_index(request):
    user_follows = Follow.objects.select_related('author').filter(user=request.user).values_list("author")
    post_list = Post.objects.filter(author__in=user_follows).order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request,
                  "follow.html",
                  {"page": page,
                   "paginator": paginator,
                   "page_number": page_number})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('profile', username=username)



@login_required
def profile_unfollow(request, username):
    author = User.objects.get(username=username)
    Follow.objects.filter(
        user=request.user,
        author=author,
    ).delete()
    return redirect('profile', username=username)