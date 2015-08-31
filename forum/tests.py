import datetime
from django.utils import timezone
from django.utils.http import urlquote
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from forum.models import Board, Thread, User, Moderation
from forum.forms import BoardForm
from djangle import settings


# Create your tests here.


class BoardTest(TestCase):
    def test_correct_creation(self):
        board1 = Board.create(name='board1 name', code='b1')
        board2 = Board.create('board2 name', 'b2')
        self.assertIsInstance(board1, Board)
        self.assertIsInstance(board2, Board)

    def test_creation_with_invalid_name(self):
        self.assertRaises(ValueError, Board.create, name='board name too long for this model really too too long',
                          code='bcode')
        self.assertRaises(TypeError, Board.create, name=None, code='bcode')

    def test_creation_with_invalid_code(self):
        self.assertRaises(ValidationError, Board.create, name='board name', code='bcod&')
        self.assertRaises(ValueError, Board.create, name='board name', code='wrongboardcode')

    def test_get_latest_without_threads(self):
        board = Board.create('board name', 'bcode')
        threads1 = board.get_latest()
        threads2 = board.get_latest(5)
        threads3 = board.get_latest('pippo')
        self.assertEqual(threads1, [])
        self.assertEqual(threads2, [])
        self.assertEqual(threads3, [])

    def test_get_latest_with_threads(self):
        board = Board.create('board name', 'bcode')
        user = User.objects.create(username='pippo', email='pippo@pluto.com')
        pub_date = timezone.now()
        thread_list = []
        for i in range(10):
            thread_list.append(Thread.create(title='thread' + str(i), message=str(i), author=user, board=board))
            thread_list[i].first_post.pub_date = pub_date - datetime.timedelta(minutes=i)
            thread_list[i].first_post.save()
        threads1 = board.get_latest()
        threads2 = board.get_latest(5)
        threads3 = board.get_latest('pippo')
        self.assertEqual(threads1, thread_list)
        self.assertEqual(threads2, thread_list[:5])
        self.assertEqual(threads3, thread_list)


class CreateBoardTest(TestCase):
    def test_view_with_anonymous_user(self):
        response = self.client.get(reverse('forum:create_board'), follow=True)
        self.assertRedirects(response, settings.LOGIN_URL + '/?next=' + urlquote(reverse('forum:create_board'), ''))

    def test_view_with_logged_user(self):
        User.objects.create_user(username='usertest', password='password', email='test@email.com')
        self.client.login(username='usertest', password='password')
        response = self.client.get(reverse('forum:create_board'), follow=True)
        self.assertEqual(response.status_code, 403)

    def test_view_with_logged_mod(self):
        mod = User.objects.create_user(username='modtest', password='password', email='test@email.com')
        board = Board.create('board', 'b')
        Moderation.objects.create(user=mod, board=board)
        self.client.login(username='modtest', password='password')
        response = self.client.get(reverse('forum:create_board'), follow=True)
        self.assertEqual(response.status_code, 403)

    def test_view_with_logged_supermod(self):
        smod = User.objects.create_user(username='smodtest', password='password', email='test@email.com')
        smod.set_supermod(True)
        self.client.login(username='smodtest', password='password')
        response = self.client.get(reverse('forum:create_board'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forum/create.html')


class BoardFormTest(TestCase):
    def test_with_correct_input(self):
        data = {'name': 'board name', 'code': 'bcode'}
        form = BoardForm(data=data)
        self.assertTrue(form.is_valid())

    def test_with_too_long_fields(self):
        data = {'name': 'board name too long for this model really too too long', 'code': 'bcode'}
        form1 = BoardForm(data=data)
        data = {'name': 'board name', 'code': 'long board code'}
        form2 = BoardForm(data=data)
        self.assertFalse(form1.is_valid())
        self.assertFalse(form2.is_valid())

    def test_with_already_existing_fields(self):
        Board.create('board name', 'bcode')
        data = {'name': 'board name', 'code': 'code'}
        form1 = BoardForm(data=data)
        data = {'name': 'other name', 'code': 'bcode'}
        form2 = BoardForm(data=data)
        self.assertFalse(form1.is_valid())
        self.assertFalse(form2.is_valid())

    def test_with_invalid_characters(self):
        data = {'name': 'board name', 'code': 'c5'}
        form1 = BoardForm(data=data)
        data = {'name': 'board name', 'code': 'c d'}
        form2 = BoardForm(data=data)
        data = {'name': 'board name', 'code': 'cod&'}
        form3 = BoardForm(data=data)
        self.assertTrue(form1.is_valid())
        self.assertFalse(form2.is_valid())
        self.assertFalse(form3.is_valid())


class BoardViewTest(TestCase):
    def test_board_view_with_no_threads(self):
        board = Board.create('boardname', 'bc')
        response = self.client.get(reverse('forum:board', kwargs={'board_code': board.code, 'page': ''}), follow=True)
        self.assertEqual(response.status_code, 200)


class ThreadViewTest(TestCase):
    def test_thread_view_with_no_responses(self):
        board = Board.create('boardname', 'bc')
        author = User.objects.create_user(username='user', password='pass', email='test@email.com')
        thread = Thread.create('thread title', 'thread message', board, author)
        response = self.client.get(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}), follow=True)
        self.assertEqual(response.status_code, 200)
