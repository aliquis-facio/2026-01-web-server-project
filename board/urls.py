from django.urls import path

from . import views


urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("create/", views.post_create, name="post_create"),
    path("<int:post_id>/", views.post_detail, name="post_detail"),
    path("<int:post_id>/edit/", views.post_update, name="post_update"),
    path("<int:post_id>/delete/", views.post_delete, name="post_delete"),
    path("<int:post_id>/download/txt/", views.download_ascii_txt, name="download_ascii_txt"),
    path("<int:post_id>/download/gif/", views.download_ascii_gif, name="download_ascii_gif"),
    path("<int:post_id>/like/", views.toggle_like, name="toggle_like"),
    path("<int:post_id>/comments/", views.comment_create, name="comment_create"),
]
