from django.urls import path
from .views import NLPParseView

urlpatterns = [
    path('nlp/', NLPParseView.as_view(), name='nlp-parse'),
]
