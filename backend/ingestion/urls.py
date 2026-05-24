from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.upload, name="upload"),
    path("records/", views.records, name="records"),
    path("records/<int:pk>/review/", views.review_record, name="review-record"),
    path("batches/", views.batches, name="batches"),
]
