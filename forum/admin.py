from django.contrib import admin
from .models import User, Post, Thread, Board, Subscription
# Register your models here.


class UserAdmin(admin.ModelAdmin):
    pass

admin.site.register(User, UserAdmin)
admin.site.register(Post)
admin.site.register(Thread)
admin.site.register(Board)
admin.site.register(Subscription)
