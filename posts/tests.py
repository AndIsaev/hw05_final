import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.test import TestCase, Client, override_settings
from .models import *
from .forms import *
from django.urls import reverse
from django.core.cache import cache



User = get_user_model()


class ProfileTest(TestCase):
    def setUp(self):
        self.auth_client = Client()
        self.user = User.objects.create_user(
            username="sarah",
            email="connor.s@skynet.com")
        self.auth_client.force_login(self.user)
        self.unauth_client = Client()


        self.group = Group.objects.create(
            title="test group",
            slug="test_group",
            description="test description")


    def test_profile(self):
        response = self.auth_client.get(
            reverse("profile", kwargs=dict(username=self.user.username)))
        self.assertEqual(response.status_code, 200)


    def test_new_post_authorized(self):
        response = self.auth_client.post(
            reverse("new_post"),
            data={
                "text": "test",
                "group": self.group.id
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 1)
        self.assertTrue(Post.objects
                        .filter(author=self.user)
                        .filter(text="test").exists()
                        )


    def test_new_post_unauthorized(self):
        response = self.unauth_client.post(
            reverse("new_post"),
            data={
                "text": "test",
                "group": self.group.id
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/auth/login/?next=/new", status_code=302,
                        target_status_code=200, msg_prefix="Редирект на вход",
                        fetch_redirect_response=True)


    def _post_for_page(self, url, post):
        response = self.auth_client.get(url)
        if "paginator" in response.context:
            posts_list = response.context['paginator'].object_list
            self.assertEqual(Post.objects.count(), 1)
            self.assertEqual(posts_list[0], post)
        else:
            self.assertEqual(response.context['post'], post)


    def test_post_for_all_pages(self):
        cache.clear()
        post = Post.objects.create(text="text",
                                   author=self.user,
                                   group=self.group
                                   )
        for url in (
            reverse("index"),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse("post", kwargs={
                    "username": self.user.username,
                    "post_id": post.id,
                })
        ):
            self._post_for_page(url=url, post=post)


    def test_edit_post(self):
        post = Post.objects.create(
            text="test",
            group=self.group,
            author=self.user)
        new_group = Group.objects.create(
            title="test_gp",
            slug="test_gp")
        kwargs = {
            "username": self.user.username,
            "post_id": post.id}
        path = reverse("post_edit",
                       kwargs=kwargs)
        data = {
            "text": "Новый текст поста!!!!",
            "group": new_group.id}
        response = self.auth_client.post(path, data=data)
        self.assertEqual(response.status_code, 302)

        for url in (
            reverse("index"),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse("post", kwargs={
                    "username": self.user.username,
                    "post_id": post.id,
                })
        ):
            self._post_for_page(url=url, post=post)
        response = self.auth_client.get(reverse("group_posts",
                                                kwargs={"slug": self.group.slug}))
        self.assertNotIn(post, response.context["paginator"].object_list)



class TestSprint06(TestCase):
    def setUp(self):
        self.auth_client = Client()
        self.text = "test"
        self.user = User.objects.create_user(
            username="sarah",
            email="connor.s@skynet.com")
        self.auth_client.force_login(self.user)
        self.unauth_client = Client()

        self.group = Group.objects.create(
            title="test group",
            slug="test_group",
            description="test description")

        self.urls = (
            reverse("index"),
            reverse("profile", kwargs={"username":self.user}),
            reverse("group_posts", kwargs={"slug": self.group.slug}))

    def test_404(self):
        self.auth_client.force_login(self.user)
        step = self.auth_client.get(f"/net_takogo/")
        response = self.auth_client.get(step)
        self.assertTemplateUsed(response, template_name="misc/404.html")


    def test_post_image(self):
        with open("media/file.jpg", "rb") as img:
            post = self.auth_client.post(
                reverse("new_post"),
                data={
                    "author": self.user,
                    "text": "test",
                    "group": self.group.id,
                    "image": img
                },
                follow=True)
        self.assertEqual(post.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

    def test_img_tag_and_txt(self):
        cache.clear()
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open("media/file.jpg", "rb") as img:
                    self.auth_client.post(
                    reverse("new_post"),
                    data={
                        "author": self.user,
                        "text": self.text,
                        "group": self.group.id,
                        "image": img
                    })

                for url in self.urls:
                    response = self.auth_client.get(url)
                    self.assertContains(response, "<img")

        """проверка txt файла"""
        with open('media/text.txt', 'rb') as img:
            post = self.auth_client.post(
                reverse('new_post'),
                data={
                    'author': self.user,
                    'text': self.text,
                    'group': self.group.id,
                    'image': img
                },
                follow=True)
        self.assertEqual(post.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)



    def test_cache_index(self):
        cache.clear()
        with self.assertNumQueries(3):
            response = self.auth_client.get(reverse('index'))
            self.assertEqual(response.status_code, 200)
            response = self.auth_client.get(reverse('index'))
            self.assertEqual(response.status_code, 200)