from __future__ import annotations

from enum import Enum


class InputFormat(str, Enum):
    AUTO = "auto"
    JSON = "json"
    PYTHON = "python"
    MONGO_EXTENDED = "mongo_extended"
    MONGO_SHELL = "mongo_shell"
    ELASTIC_HIT = "elastic_hit"
    ELASTIC_SOURCE = "elastic_source"


class OutputFormat(str, Enum):
    PYTHON = "python"
    JSON = "json"
    MONGO_EXTENDED = "mongo_extended"
    MONGO_SHELL = "mongo_shell"
    ELASTIC_HIT = "elastic_hit"
    ELASTIC_SOURCE = "elastic_source"


INPUT_FORMAT_VALUES = tuple(fmt.value for fmt in InputFormat)
OUTPUT_FORMAT_VALUES = tuple(fmt.value for fmt in OutputFormat)
