from django.db import models


class Survey(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    class QuestionType(models.TextChoices):
        SHORT_TEXT = "short_text", "Short Text"
        LONG_TEXT = "long_text", "Long Text"
        EMAIL = "email", "Email"
        CHOICE = "choice", "Choice"      
        FILE = "file", "File Upload"

    survey = models.ForeignKey(Survey, related_name="questions", on_delete=models.CASCADE)
    name = models.SlugField(max_length=100)  # machine key, e.g. "full_name"
    type = models.CharField(max_length=20, choices=QuestionType.choices)
    text = models.CharField(max_length=500)
    description = models.CharField(max_length=500, blank=True, default="")
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    # only relevant when type == "choice": controls <options multiple="yes|no">
    allow_multiple = models.BooleanField(default=False)

    # file-question-only settings
    file_format = models.CharField(max_length=20, blank=True, default=".pdf")
    max_file_size_mb = models.PositiveIntegerField(default=1)
    file_multiple = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("survey", "name")

    def __str__(self):
        return f"{self.survey.name} - {self.text}"

    @property
    def is_choice(self):
        return self.type == self.QuestionType.CHOICE

class Option(models.Model):
    question = models.ForeignKey(Question, related_name="options", on_delete=models.CASCADE)
    value = models.CharField(max_length=100)  
    label = models.CharField(max_length=255)   
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("question", "value")

    def __str__(self):
        return f"{self.question.name}:{self.value}"


class Response(models.Model):
    survey = models.ForeignKey(Survey, related_name="responses", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True, default="")
    email_address = models.EmailField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Response #{self.id} to {self.survey.name}"


class Answer(models.Model):
    response = models.ForeignKey(Response, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE)
    # holds text/email answers, or comma-joined option values for choice questions
    value = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("response", "question")

    def __str__(self):
        return f"{self.question.name} = {self.value}"


def certificate_upload_path(instance, filename):
    return f"certificates/response_{instance.answer.response_id}/{filename}"


class Certificate(models.Model):
    answer = models.ForeignKey(Answer, related_name="certificates", on_delete=models.CASCADE)
    file = models.FileField(upload_to=certificate_upload_path)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename
