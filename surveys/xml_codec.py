"""
Hand-built XML encoding/decoding so our API output matches the exact
shapes in the task spec (attributes on root tags, self-closing empty
elements, etc). We use xml.etree.ElementTree rather than a generic
serializer-to-XML mapper because the spec's shapes are irregular
(e.g. <survey id="1"> has an attribute, but <name> is a plain element).
"""
import math
import xml.etree.ElementTree as ET



# ---------- small helpers ----------

def _text(elem, tag, default=""):
    """Read the text of a child element, or return default if missing/empty."""
    child = elem.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _bool_attr(value):
    return "yes" if value else "no"


def _to_xml_bytes(root):
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode").encode("utf-8")


# ---------- Survey ----------

def parse_survey_payload(xml_bytes):
    """POST /api/surveys request body -> {"name": ..., "description": ...}"""
    root = ET.fromstring(xml_bytes)
    return {
        "name": _text(root, "name"),
        "description": _text(root, "description"),
    }


def render_survey_element(survey):
    el = ET.Element("survey", {"id": str(survey.id)})
    ET.SubElement(el, "name").text = survey.name
    desc = ET.SubElement(el, "description")
    desc.text = survey.description or None
    return el


def render_survey(survey):
    """Single <survey> document — used as the response after create/update."""
    return _to_xml_bytes(render_survey_element(survey))


def render_surveys(surveys):
    """<surveys><survey id="1">...</survey>...</surveys> — used for GET /api/surveys"""
    root = ET.Element("surveys")
    for survey in surveys:
        root.append(render_survey_element(survey))
    return _to_xml_bytes(root)


# ---------- Question ----------

def parse_question_payload(xml_bytes):
    """
    POST /api/surveys/{id}/questions request body ->
    {"name", "type", "required", "text", "description", "allow_multiple", "options": [(value, label), ...]}
    """
    root = ET.fromstring(xml_bytes)
    data = {
        "name": root.attrib.get("name", ""),
        "type": root.attrib.get("type", ""),
        "required": root.attrib.get("required", "yes") == "yes",
        "text": _text(root, "text"),
        "description": _text(root, "description"),
        "allow_multiple": False,
        "options": [],
    }
    options_el = root.find("options")
    if options_el is not None:
        data["allow_multiple"] = options_el.attrib.get("multiple", "no") == "yes"
        for opt in options_el.findall("option"):
            data["options"].append({
                "value": opt.attrib.get("value", ""),
                "label": (opt.text or "").strip(),
            })
    return data


def render_question_element(question):
    el = ET.Element("question", {
        "id": str(question.id),
        "name": question.name,
        "type": question.type,
        "required": _bool_attr(question.required),
    })
    ET.SubElement(el, "text").text = question.text
    desc = ET.SubElement(el, "description")
    desc.text = question.description or None

    if question.is_choice:
        options_el = ET.SubElement(el, "options", {"multiple": _bool_attr(question.allow_multiple)})
        for option in question.options.all():
            opt_el = ET.SubElement(options_el, "option", {"value": option.value})
            opt_el.text = option.label

    if question.type == question.QuestionType.FILE:
        ET.SubElement(el, "file_properties", {
            "format": question.file_format,
            "max_file_size": str(question.max_file_size_mb),
            "max_file_size_unit": "mb",
            "multiple": _bool_attr(question.file_multiple),
        })
    return el


def render_question(question):
    return _to_xml_bytes(render_question_element(question))


def render_questions(questions):
    root = ET.Element("questions")
    for question in questions:
        root.append(render_question_element(question))
    return _to_xml_bytes(root)

def render_error(message):
    root = ET.Element("error")
    root.text = message
    return _to_xml_bytes(root)

# ---------- Response ----------

def _render_question_response_element(response, survey, include_response_id, include_certificate_id):
    """
    Builds a <question_response> element. The child element for each
    question is named after that question's `name` (dynamic, per the
    survey's own schema) — e.g. <full_name>, <gender>, <certificates>.
    """
    el = ET.Element("question_response")

    if include_response_id:
        ET.SubElement(el, "response_id").text = str(response.id)

    # full_name and email_address are captured on every response
    # regardless of whether the survey also happens to define a question
    # with a matching name — render them straight from the Response record
    # so they never go missing.
    ET.SubElement(el, "full_name").text = response.full_name or None
    ET.SubElement(el, "email_address").text = response.email_address or None

    answers_by_question_id = {a.question_id: a for a in response.answers.all()}

    for question in survey.questions.all():
        if question.name in ("full_name", "email_address"):
            continue  # already rendered above from the Response record

        answer = answers_by_question_id.get(question.id)

        if question.type == question.QuestionType.FILE:
            wrapper = ET.SubElement(el, question.name)
            if answer:
                for cert in answer.certificates.all():
                    attrs = {"id": str(cert.id)} if include_certificate_id else {}
                    cert_el = ET.SubElement(wrapper, "certificate", attrs)
                    cert_el.text = cert.original_filename
        else:
            value_el = ET.SubElement(el, question.name)
            value_el.text = (answer.value if answer else "") or None

    ET.SubElement(el, "date_responded").text = response.submitted_at.strftime("%Y-%m-%d %H:%M:%S")
    return el


def render_response_confirmation(response, survey):
    """Returned right after POST /api/surveys/{id}/responses"""
    el = _render_question_response_element(
        response, survey, include_response_id=False, include_certificate_id=False
    )
    return _to_xml_bytes(el)


def render_responses(responses, survey, page, page_size, total_count):
    """<question_responses current_page=... last_page=... page_size=... total_count=...>"""
    last_page = max(1, math.ceil(total_count / page_size)) if page_size else 1
    root = ET.Element("question_responses", {
        "current_page": str(page),
        "last_page": str(last_page),
        "page_size": str(page_size),
        "total_count": str(total_count),
    })
    for response in responses:
        root.append(_render_question_response_element(
            response, survey, include_response_id=True, include_certificate_id=True
        ))
    return _to_xml_bytes(root)