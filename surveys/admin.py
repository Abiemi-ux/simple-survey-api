from django.contrib import admin
from .models import Survey, Question, Option, Response, Answer, Certificate


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ("order", "name", "type", "text", "required")
    show_change_link = True


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    search_fields = ("name",)
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "name", "type", "required", "order")
    list_filter = ("survey", "type")
    inlines = [OptionInline]


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ("question", "value")
    can_delete = False


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "full_name", "email_address", "submitted_at")
    list_filter = ("survey",)
    search_fields = ("email_address", "full_name")
    inlines = [AnswerInline]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "answer", "uploaded_at")
