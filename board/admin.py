from django.contrib import admin

from .models import AsciiFrame, Comment, Like, Post


class AsciiFrameInline(admin.TabularInline):
    model = AsciiFrame
    extra = 0
    readonly_fields = ("frame_index", "created_at")
    fields = ("frame_index", "created_at")
    can_delete = False


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "media_type", "status", "view_count", "created_at")
    list_filter = ("media_type", "status", "char_style", "created_at")
    search_fields = ("title", "content", "author__username")
    inlines = [AsciiFrameInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    search_fields = ("content", "author__username", "post__title")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
