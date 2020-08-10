import io
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.core.files.uploadedfile import SimpleUploadedFile
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
        self.assertRedirects(response, "/auth/login/?next=/new",
                             status_code=302,
                        target_status_code=200,
                             msg_prefix="Редирект на вход",
                        fetch_redirect_response=True)


    def _post_for_page(self, url, group, user, text):
        cache.clear()
        response = self.auth_client.get(url)
        if 'paginator' in response.context:
            current_post = response.context['paginator'].object_list.first()
        else:
            current_post = response.context['post']
        self.assertEqual(current_post.text, text)
        self.assertEqual(current_post.group, group)
        self.assertEqual(current_post.author, user)


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
            with self.subTest(url=url):
                self._post_for_page(url, post.group, post.author, post.text)


    def test_edit_post(self):
        cache.clear()
        new_group = Group.objects.create(title="lola", slug="lola")
        post = Post.objects.create(text="text",
                                   author=self.user,
                                   group=self.group)
        post_text = "edit_text"
        post_id = post.id
        self.auth_client.post(
            reverse(
                "post_edit",
                kwargs={"username": self.user.username,
                        "post_id": post_id, },
            ),
            data={"text": post_text, "group": new_group.id},
            follow=True,
        )
        post = Post.objects.get(id=post.id)
        for url in (
                reverse("index"),
                reverse("profile", kwargs={"username": self.user.username}),
                reverse("post", kwargs={
                    "username": self.user.username,
                    "post_id": post.id,
                })
        ):
            self._post_for_page(url, post.group, post.author, post.text)
        response = self.auth_client.get(
            reverse("group_posts", kwargs={"slug": self.group.slug})
        )
        self.assertNotIn(post, response.context["paginator"].object_list)


class TestSprintTheory06(TestCase):
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
        step = self.auth_client.get("/net_takogo/")
        response = self.auth_client.get(step)
        self.assertTemplateUsed(response, template_name="misc/404.html")


    def test_post_image(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
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


    def test_img_tag(self):
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


    def test_txt_error(self):
        cache.clear()
        img_bytes = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        image = SimpleUploadedFile("small.txt", img_bytes,
                                   content_type="text/plain")
        post_data = {"text": "test post",
                     "group": self.group.id, "image": image}
        text_error = "Формат файлов 'txt' не поддерживается. Поддерживаемые " \
                     "форматы файлов: 'bmp, dib, gif, tif, tiff, jfif, " \
                     "jpe, jpg, jpeg, pbm, pgm, ppm, pnm, png, apng, blp, " \
                     "bufr, cur, pcx, dcx, dds, ps, eps, fit, " \
                     "fits, fli, flc, ftc, ftu, gbr, grib, h5, hdf, " \
                     "jp2, j2k, jpc, jpf, jpx, j2c, icns, ico, im, " \
                     "iim, mpg, mpeg, mpo, msp, palm, pcd, pdf, pxr, psd, " \
                     "bw, rgb, rgba, sgi, ras, tga, icb, vda, " \
                     "vst, webp, wmf, emf, xbm, xpm'."
        response = self.auth_client.post(reverse("new_post"), data=post_data)
        self.assertFormError(response, form="form", field="image",
                             errors=text_error)


    def test_cache_index(self):
        cache.clear()
        with self.assertNumQueries(3):
            response = self.auth_client.get(reverse("index"))
            self.assertEqual(response.status_code, 200)
            response = self.auth_client.get(reverse("index"))
            self.assertEqual(response.status_code, 200)



class TestFollow(TestCase):
    def setUp(self):
        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.user_follower = User.objects.create_user(
            username="follower", email="true@true.com",
            password="lalalend!123"
        )
        self.user_following = User.objects.create_user(
            username="following", email="false@false.ru",
            password="kokoshanel123!"
        )
        self.client_auth_follower.force_login(self.user_follower)
        self.client_auth_following.force_login(self.user_following)
        self.comment = "test"
        self.group = Group.objects.create(
            title="test group",
            slug="test_group",
            description="test description")
        self.text = "test"

        self.cool_user = User.objects.create_user(
            username="sarah", email="connor@yandex.ru", password="sarah"
        )
        self.client.force_login(self.cool_user)
        self.unauth_client = Client()


    def test_follow(self):
        before = Follow.objects.count()
        self.client_auth_follower.get(
            reverse(
                "profile_follow",
                kwargs={
                    "username": self.user_following.username,
                },
            )
        )
        after = Follow.objects.count()
        self.assertEqual(before + 1, after)


    def test_unfollow(self):
        before = Follow.objects.count()
        self.client_auth_follower.get(
            reverse(
                "profile_follow",
                kwargs={
                    "username": self.user_following.username,
                },
            )
        )
        after = Follow.objects.count()
        self.assertEqual(before + 1, after)
        self.client_auth_follower.get(
            reverse(
                "profile_follow",
                kwargs={
                    "username": self.user_following.username,
                },
            )
        )
        self.assertEqual(after - 1, 0)


    def test_comment(self):
        cache.clear()
        self.post = Post.objects.create(text="Hello world",
                                        author=self.user_follower)
        self.assertEqual(Post.objects.count(), 1)
        comment = "Спасибо самому лучшему ревьюеру, за терпение!:)"
        post_id = self.post.id
        self.client_auth_follower.post(
            reverse(
                "add_comment",
                kwargs={"username": self.user_follower.username,
                        "post_id": post_id },
            ),
            data={"text": comment},
            follow=True
        )
        response = self.client_auth_following.get(
            reverse(
                "post",
                    kwargs={
                    "username": self.user_follower.username,
                    "post_id": post_id,
                }
                    )
        )
        self.assertContains(response, comment)


    def test_text_for_follower(self):
        before = Follow.objects.all().count()
        self.client_auth_follower.get(
            reverse(
                "profile_follow",
                kwargs={
                    "username": self.user_following.username,
                },
            )
        )
        self.assertEqual(before + 1, 1)

        post = self.client_auth_following.post(
            reverse("new_post"),
            data={
                "author": self.user_following,
                "text": self.text,
                "group": self.group.id,
            },
            follow=True)
        self.assertEqual(post.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        """подписчик проверяет пост и наличие автора"""
        response = self.client_auth_follower.get(
            reverse("follow_index")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.text)
        self.assertContains(response, self.user_following)


    def test_for_not_follower(self):
        post = self.client_auth_following.post(
            reverse("new_post"),
            data={
                "author": self.user_following,
                "text": self.text,
                "group": self.group.id,
            },
            follow=True)
        self.assertEqual(post.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        step = self.client.get(
            reverse("follow_index")
        )
        self.assertEqual(step.status_code, 200)
        self.assertNotContains(step, self.text)
        self.assertNotContains(step, self.user_following)
