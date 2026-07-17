from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.paginator import Paginator
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser

from .models import Answer, Certificate
from .models import Response as SurveyResponse

from . import xml_codec
from .models import Option, Question, Survey


class SurveyListCreateView(APIView):
    """
    GET  /api/surveys   -> list all surveys
    POST /api/surveys   -> create a survey
    """

    def get(self, request):
        surveys = Survey.objects.all().order_by("id")
        return Response(xml_codec.render_surveys(surveys))

    def post(self, request):
        data = xml_codec.parse_survey_payload(request.data)
        if not data["name"]:
            return Response(xml_codec.render_error("name is required"), status=status.HTTP_400_BAD_REQUEST)
        survey = Survey.objects.create(name=data["name"], description=data["description"])
        return Response(xml_codec.render_survey(survey), status=status.HTTP_201_CREATED)


class SurveyDetailView(APIView):
    """
    GET    /api/surveys/{id}   -> view a single survey
    PUT    /api/surveys/{id}   -> edit a survey
    DELETE /api/surveys/{id}   -> delete a survey
    """

    def get_object(self, survey_id):
        try:
            return Survey.objects.get(pk=survey_id)
        except Survey.DoesNotExist:
            return None

    def get(self, request, survey_id):
        survey = self.get_object(survey_id)
        if survey is None:
            return Response(xml_codec.render_error("Survey not found"), status=status.HTTP_404_NOT_FOUND)
        return Response(xml_codec.render_survey(survey))

    def put(self, request, survey_id):
        survey = self.get_object(survey_id)
        if survey is None:
            return Response(xml_codec.render_error("Survey not found"), status=status.HTTP_404_NOT_FOUND)
        data = xml_codec.parse_survey_payload(request.data)
        if data["name"]:
            survey.name = data["name"]
        survey.description = data["description"]
        survey.save()
        return Response(xml_codec.render_survey(survey))

    def delete(self, request, survey_id):
        survey = self.get_object(survey_id)
        if survey is None:
            return Response(xml_codec.render_error("Survey not found"), status=status.HTTP_404_NOT_FOUND)
        survey.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionListCreateView(APIView):
    """
    GET  /api/surveys/{surveyId}/questions   -> list a survey's questions
    POST /api/surveys/{surveyId}/questions   -> add a question to a survey
    """

    def get_survey(self, survey_id):
        try:
            return Survey.objects.get(pk=survey_id)
        except Survey.DoesNotExist:
            return None

    def get(self, request, survey_id):
        survey = self.get_survey(survey_id)
        if survey is None:
            return Response(xml_codec.render_error("Survey not found"), status=status.HTTP_404_NOT_FOUND)
        return Response(xml_codec.render_questions(survey.questions.all()))

    def post(self, request, survey_id):
        survey = self.get_survey(survey_id)
        if survey is None:
            return Response(xml_codec.render_error("Survey not found"), status=status.HTTP_404_NOT_FOUND)

        data = xml_codec.parse_question_payload(request.data)
        if not data["name"] or not data["type"]:
            return Response(xml_codec.render_error("name and type are required"), status=status.HTTP_400_BAD_REQUEST)

        question = Question.objects.create(
            survey=survey,
            name=data["name"],
            type=data["type"],
            text=data["text"],
            description=data["description"],
            required=data["required"],
            allow_multiple=data["allow_multiple"],
            order=survey.questions.count() + 1,
        )
        for i, opt in enumerate(data["options"], start=1):
            Option.objects.create(question=question, value=opt["value"], label=opt["label"], order=i)

        return Response(xml_codec.render_question(question), status=status.HTTP_201_CREATED)


class QuestionDetailView(APIView):
    """
    GET    /api/surveys/{surveyId}/questions/{id}   -> view a single question
    PUT    /api/surveys/{surveyId}/questions/{id}   -> edit a question (also replaces its options)
    DELETE /api/surveys/{surveyId}/questions/{id}   -> delete a question
    """

    def get_object(self, survey_id, question_id):
        try:
            return Question.objects.get(pk=question_id, survey_id=survey_id)
        except Question.DoesNotExist:
            return None

    def get(self, request, survey_id, question_id):
        question = self.get_object(survey_id, question_id)
        if question is None:
            return Response(xml_codec.render_error("Question not found"), status=status.HTTP_404_NOT_FOUND)
        return Response(xml_codec.render_question(question))

    def put(self, request, survey_id, question_id):
        question = self.get_object(survey_id, question_id)
        if question is None:
            return Response(xml_codec.render_error("Question not found"), status=status.HTTP_404_NOT_FOUND)

        data = xml_codec.parse_question_payload(request.data)
        question.name = data["name"] or question.name
        question.type = data["type"] or question.type
        question.text = data["text"]
        question.description = data["description"]
        question.required = data["required"]
        question.allow_multiple = data["allow_multiple"]
        question.save()

        # simplest way to support add/edit/remove options: replace them wholesale
        question.options.all().delete()
        for i, opt in enumerate(data["options"], start=1):
            Option.objects.create(question=question, value=opt["value"], label=opt["label"], order=i)

        return Response(xml_codec.render_question(question))

    def delete(self, request, survey_id, question_id):
        question = self.get_object(survey_id, question_id)
        if question is None:
            return Response(xml_codec.render_error("Question not found"), status=status.HTTP_404_NOT_FOUND)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ResponseListCreateView(APIView):
    """
    GET  /api/surveys/{surveyId}/responses   -> paginated, filterable list of responses
    POST /api/surveys/{surveyId}/responses   -> submit a response (multipart/form-data)
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_survey(self, survey_id):
        try:
            return Survey.objects.get(pk=survey_id)
        except Survey.DoesNotExist:
            return None

    def get(self, request, survey_id):
        survey = self.get_survey(survey_id)
        if survey is None:
            return Response(xml_codec.render_error("Survey not found"), status=status.HTTP_404_NOT_FOUND)

        queryset = survey.responses.all()
        email = request.query_params.get("email")
        if email:
            queryset = queryset.filter(email_address__icontains=email)

        page_number = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 10))

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)

        xml = xml_codec.render_responses(page_obj.object_list, survey, page_number, page_size, paginator.count)
        return Response(xml)

    def post(self, request, survey_id):
        survey = self.get_survey(survey_id)
        if survey is None:
            return Response(xml_codec.render_error("Survey not found"), status=status.HTTP_404_NOT_FOUND)

        questions = list(survey.questions.all())

        # required-field validation
        missing = []
        for q in questions:
            if not q.required:
                continue
            if q.type == q.QuestionType.FILE:
                if not request.FILES.getlist(q.name):
                    missing.append(q.name)
            elif q.is_choice and q.allow_multiple:
                if not request.data.getlist(q.name):
                    missing.append(q.name)
            elif not request.data.get(q.name):
                missing.append(q.name)
        if missing:
            return Response(
                xml_codec.render_error(f"Missing required field(s): {', '.join(missing)}"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        survey_response = SurveyResponse.objects.create(
            survey=survey,
            full_name=request.data.get("full_name", ""),
            email_address=request.data.get("email_address", ""),
        )

        for q in questions:
            if q.type == q.QuestionType.FILE:
                answer = Answer.objects.create(response=survey_response, question=q, value="")
                for f in request.FILES.getlist(q.name):
                    Certificate.objects.create(answer=answer, file=f, original_filename=f.name)
            elif q.is_choice and q.allow_multiple:
                values = request.data.getlist(q.name)
                Answer.objects.create(response=survey_response, question=q, value=",".join(values))
            else:
                Answer.objects.create(response=survey_response, question=q, value=request.data.get(q.name, ""))

        return Response(
            xml_codec.render_response_confirmation(survey_response, survey),
            status=status.HTTP_201_CREATED,
        )


class CertificateDownloadView(APIView):
    """
    GET /api/certificates/{id}  -> download a certificate file
    """

    def get(self, request, certificate_id):
        try:
            certificate = Certificate.objects.get(pk=certificate_id)
        except Certificate.DoesNotExist:
            return Response(xml_codec.render_error("Certificate not found"), status=status.HTTP_404_NOT_FOUND)

        return FileResponse(
            certificate.file.open("rb"),
            as_attachment=True,
            filename=certificate.original_filename,
        )