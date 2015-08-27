from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import User, Post, Thread, Board, Subscription, Moderation, Ban

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {
            'fields': [
                'username',
                'password',
                'first_name',
                'last_name',
                'email',
                'date_joined',
                'last_login',
                'rep',
                'is_active',
                'is_superuser',
                'is_staff',
                'avatar',
                'image_tag'
            ]
        })
    ]
    readonly_fields = ['image_tag']
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff']
    list_filter = ['date_joined', 'last_login', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def save_model(self, request, obj, form, change):
        if change:
            user = User.objects.get(username=obj.username)
            #hash the new password
            if user.password != obj.password:
                obj.password=make_password(obj.password)
            obj.save()


class PostAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['thread', 'message', 'author', 'pos_votes', 'neg_votes', 'pub_date']})
    ]
    list_display = ['message', 'thread', 'author', 'pub_date']
    list_filter = ['pub_date']
    search_fields = ['message']


class FirstPostInline(admin.TabularInline):
    model = Post
    max_num = 1
    verbose_name_plural = 'Posts'
    can_delete = False
    fieldsets = [
        (None, {'fields': ['message', 'author', 'pos_votes', 'neg_votes', 'pub_date']})
    ]


class ThreadAdmin(admin.ModelAdmin):
    inlines = [FirstPostInline]
    fieldsets = [
        (None, {'fields': ['title','first_post', 'board', 'sticky']}),
        ('Tags', {'fields': ['tag1', 'tag2', 'tag3']}),
        ('Closing information', {'fields': ['close_date', 'closer'], 'classes': ['collapse']})
    ]
    list_display = ['title', 'board', 'sticky', 'closed']
    list_display_links = ['title', 'sticky']
    list_filter = ['board', 'sticky', 'close_date']
    search_fields = ['title', 'tag1', 'tag2', 'tag3']

    def closed(self, obj):
        if obj.close_date is not None:
            return 'Closed on '+obj.close_date.strftime('%Y-%m-%d %H:%M')+' from '+str(obj.closer)
        else:
            return 'Open'
    closed.admin_order_field = 'close_date'

    def save_model(self, request, obj, form, change):
        if obj.first_post is None and self.inlines is not None:
            post = obj.post_set.last()
            obj.first_post = post
        obj.save()

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'first_post':
            kwargs["queryset"] = Post.objects.order_by('-pub_date')
        return super(ThreadAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class BoardAdmin(admin.ModelAdmin):
    def num_threads(self, obj):
        return obj.thread_set.count()
    num_threads.short_description = 'Threads number'

    def num_mods(self, obj):
        return obj.moderation_set.count()
    num_mods.short_description = 'Moderators number'

    list_display = ['code', 'name', 'num_threads', 'num_mods']
    list_display_links = ['code', 'name']
    search_fields = ['name', 'code']


class SubscriptionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['user', 'thread', 'async', 'sync_interval', 'last_sync', 'active']})
    ]
    list_display = ['user', 'thread', 'active']
    search_fields = ['user__username', 'thread__title']
    list_filter = ['active']



class ModerationAdmin(admin.ModelAdmin):
    list_display = ['user', 'board']
    search_fields = ['user__username']
    list_filter = ['board']


class BanAdmin(admin.ModelAdmin):
    def active(self, obj):
        if obj.is_active:
            return True
        else:
            return False
    active.boolean = True

    list_display = ['user', 'start', 'duration', 'banner', 'reason', 'active']
    list_filter = ['start', 'duration']
    search_fields = ['user__username', 'banner__username']


admin.site.register(User, UserAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Thread, ThreadAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Moderation, ModerationAdmin)
admin.site.register(Ban, BanAdmin)
