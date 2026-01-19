# Maps URLs for each Django application

from django.urls import path, include

urlpatterns = [
    path('', include('chat.urls')),
]
