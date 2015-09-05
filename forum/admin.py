from django.contrib import admin
from django.contrib.admin.widgets import AdminFileWidget
from django.contrib.auth.hashers import make_password
from django.utils.safestring import mark_safe
from djangle.settings import MEDIA_URL
from .models import User, Post, Thread, Board, Subscription, Moderation, Ban, Comment

# Register your models here.


class AdminImageWidget(AdminFileWidget):
    """
    a widget that displays an image
    """
    def render(self, name, value, attrs=None):
        output = []
        if value:
            file_path = '%s%s' % (MEDIA_URL, value)
            output.append('<a target="_blank" href="%s"><img src="%s" height="200"></a><br />' % (file_path, file_path))
        output.append(super(AdminImageWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))


class UserAdmin(admin.ModelAdmin):
    """
    representation of User model in the admin interface
    """
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'avatar':
            kwargs.pop("request", None)
            kwargs['widget'] = AdminImageWidget
            return db_field.formfield(**kwargs)
        return super(UserAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    fieldsets = [
        (None, {
            'fields': [
                'username',
                'password',
                ('first_name', 'last_name'),
                'email',
                ('date_joined', 'last_login'),
                'avatar'
            ]
        }),
        ('User status', {'fields': ['rep', 'is_active', 'is_superuser', 'is_staff']})
    ]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff']
    list_filter = ['date_joined', 'last_login', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def save_model(self, request, obj, form, change):
        """
        given a model instance, save it to the database

        saves model instance to the database. If password was changed, hashes it before saving

        :param request: the HttpRequest
        :param obj: User instance
        :param form: ModelForm instance
        :param change: boolean value based on whether it is adding or changing the object
        :return: nothing
        """
        user = None
        if change:
            user = User.objects.get(username=obj.username)
        if not change or user.password != obj.password:
            obj.password = make_password(obj.password)
        obj.save()


class PostAdmin(admin.ModelAdmin):
    """
    representation of Post model in the admin interface
    """
    readonly_fields = ['pos_votes', 'neg_votes']
    fieldsets = [
        (None, {'fields': ['thread', 'message', 'author', 'pub_date', ('pos_votes', 'neg_votes')]})
    ]
    list_display = ['__str__', 'thread', 'author', 'pub_date']
    list_filter = ['pub_date']
    search_fields = ['message']


class ThreadAdmin(admin.ModelAdmin):
    """
    representation of Thread model in the admin interface
    """
    fieldsets = [
        (None, {'fields': ['title', 'first_post', 'board', 'sticky']}),
        ('Tags', {'fields': ['tag1', 'tag2', 'tag3']}),
        ('Closing information', {'fields': ['close_date', 'closer'], 'classes': ['collapse']})
    ]

    list_display = ['title', 'board', 'sticky', 'closed', 'tags']
    list_display_links = ['title', 'sticky']
    list_filter = ['board', 'sticky', 'close_date']
    search_fields = ['title', 'tag1', 'tag2', 'tag3']

    @staticmethod
    def closed(obj):
        """
        return a string with information about the closure of the thread

        :param obj: Thread instance
        :return: a string
        """
        if obj.close_date is not None:
            return 'Closed on ' + obj.close_date.strftime('%Y-%m-%d %H:%M') + ' from ' + str(obj.closer)
        else:
            return 'Open'
    closed.admin_order_field = 'close_date'

    @staticmethod
    def tags(obj):
        """
        returns a string formed by the thread's tags separated with a comma

        :param obj: Thread instance
        :return: string of tags
        """
        return ', '.join(obj.get_tags())

    def save_model(self, request, obj, form, change):
        """
        given a model instance, save it to the database

        saves model instance to the database. Automatically update first_post field.

        :param request: the HttpRequest
        :param obj: Thread instance
        :param form: ModelForm instance
        :param change: boolean value based on whether it is adding or changing the object
        :return: nothing
        """
        if obj.first_post is None and self.inlines is not None:
            post = obj.post_set.first()
            obj.first_post = post
        obj.save()


class BoardAdmin(admin.ModelAdmin):
    """
    representation of Board model in the admin interface
    """
    @staticmethod
    def num_threads(obj):
        """
        method to get the number of threads of the board

        :param obj: Board instance
        :return: the number of thread in the board
        """
        return obj.thread_set.count()
    num_threads.short_description = 'Threads number'

    @staticmethod
    def num_mods(obj):
        """
        method to get the number of moderators for the board

        :param obj: Board instance
        :return: the number of moderators of the board
        """
        return obj.moderation_set.count()
    num_mods.short_description = 'Moderators number'

    list_display = ['code', 'name', 'num_threads', 'num_mods']
    list_display_links = ['code', 'name']
    search_fields = ['name', 'code']


class SubscriptionAdmin(admin.ModelAdmin):
    """
    representation of Subscription model in the admin interface
    """
    fieldsets = [
        (None, {'fields': ['user', 'thread', 'async', 'sync_interval', 'last_sync', 'active']})
    ]
    list_display = ['user', 'thread', 'active']
    search_fields = ['user__username', 'thread__title']
    list_filter = ['active']


class ModerationAdmin(admin.ModelAdmin):
    """
    representation of Moderation model in the admin interface
    """
    list_display = ['user', 'board']
    search_fields = ['user__username']
    list_filter = ['board']


class BanAdmin(admin.ModelAdmin):
    """
    representation of Ban model in the admin interface
    """
    @staticmethod
    def active(obj):
        """
        method to get if the ban is active

        :param obj: Ban instance
        :return: boolean value based on whether it active or not
        """
        if obj.is_active:
            return True
        else:
            return False
    active.boolean = True

    list_display = ['user', 'start', 'duration', 'banner', 'reason', 'active']
    list_filter = ['start', 'duration']
    search_fields = ['user__username', 'banner__username']


class CommentAdmin(admin.ModelAdmin):
    """
    representation of Comment model in the admin interface
    """
    readonly_fields = ['pos_votes', 'neg_votes']
    fieldsets = [
        (None, {'fields': ['post', 'message', 'author', 'pub_date', ('pos_votes', 'neg_votes')]})
    ]

    list_display = ['__str__', 'post', 'author', 'pub_date']
    list_filter = ['pub_date']
    search_fields = ['message']


admin.site.register(User, UserAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Thread, ThreadAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Moderation, ModerationAdmin)
admin.site.register(Ban, BanAdmin)
admin.site.register(Comment, CommentAdmin)
