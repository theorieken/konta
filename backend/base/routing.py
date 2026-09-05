from django.urls import path

from base.consumers import EventsConsumer

websocket_urlpatterns = [
    path("ws/events/", EventsConsumer.as_asgi()),
]
