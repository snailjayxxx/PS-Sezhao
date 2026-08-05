"""Stable processing contracts shared by services and storage."""

from dataclasses import dataclass


MATH_CONTRACT_VERSION = 1
RAW_DECODE_CONTRACT_VERSION = 1
PROXY_CONTRACT_VERSION = 1
OUTPUT_QUEUE_CONTRACT_VERSION = 2
OUTPUT_SETTINGS_CONTRACT_VERSION = 1
GEOMETRY_CONTRACT_VERSION = 1
PROJECT_SCHEMA_VERSION = 4


@dataclass(frozen=True)
class ProcessingContract:
    math_version: int = MATH_CONTRACT_VERSION
    raw_decode_version: int = RAW_DECODE_CONTRACT_VERSION
    proxy_version: int = PROXY_CONTRACT_VERSION
    output_queue_version: int = OUTPUT_QUEUE_CONTRACT_VERSION
    output_settings_version: int = OUTPUT_SETTINGS_CONTRACT_VERSION
    geometry_version: int = GEOMETRY_CONTRACT_VERSION
    project_schema_version: int = PROJECT_SCHEMA_VERSION


CURRENT_PROCESSING_CONTRACT = ProcessingContract()
