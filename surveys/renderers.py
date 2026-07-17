from rest_framework.renderers import BaseRenderer
from rest_framework.parsers import BaseParser


class XMLRenderer(BaseRenderer):
    """
    Views build the final XML themselves (via xml_codec.py) and pass the
    resulting bytes straight through as `data`. This renderer just sets
    the right content type instead of trying to auto-serialize.
    """
    media_type = "application/xml"
    format = "xml"
    charset = None  # data is already encoded bytes

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, bytes):
            return data
        return str(data).encode("utf-8")


class XMLParser(BaseParser):
    """
    Reads the raw XML request body and hands the bytes to the view.
    Views call the relevant xml_codec.parse_*_payload() function themselves,
    since the payload shape differs per endpoint.
    """
    media_type = "application/xml"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()