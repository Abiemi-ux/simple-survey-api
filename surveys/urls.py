from django.urls import path
from . import views

urlpatterns = [
    path("surveys", views.SurveyListCreateView.as_view(), name="survey-list-create"),
    path("surveys/<int:survey_id>", views.SurveyDetailView.as_view(), name="survey-detail"),
    path("surveys/<int:survey_id>/questions", views.QuestionListCreateView.as_view(), name="question-list-create"),
    path("surveys/<int:survey_id>/questions/<int:question_id>", views.QuestionDetailView.as_view(), name="question-detail"),
    path("surveys/<int:survey_id>/responses", views.ResponseListCreateView.as_view(), name="response-list-create"),
    path("certificates/<int:certificate_id>", views.CertificateDownloadView.as_view(), name="certificate-download"),
]