from django.urls import path

from .views import ThreadListView, ThreadDetailView, ActorListView, ChatView, ActorDetailView

app_name = "actors-api"
urlpatterns = [
    path("threads/", ThreadListView.as_view(), name='threads'),
    path("threads/<str:id>/", ThreadDetailView.as_view(), name='threads'),
    path("actors/", ActorListView.as_view(), name='actors'),
    path("actors/<str:name>/", ActorDetailView.as_view(), name='actors'),
    path("chat/", ChatView.as_view(), name='chat'),
]