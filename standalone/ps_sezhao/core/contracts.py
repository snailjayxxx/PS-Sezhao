"""Stable processing contracts shared by services and storage."""

from dataclasses import dataclass


MATH_CONTRACT_VERSION = 1
RAW_DECODE_CONTRACT_VERSION = 1
PROXY_CONTRACT_VERSION = 1
PROJECT_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class ProcessingContract:
    math_version: int = MATH_CONTRACT_VERSION
    raw_decode_version: int = RAW_DECODE_CONTRACT_VERSION
    proxy_version: int = PROXY_CONTRACT_VERSION
    project_schema_version: int = PROJECT_SCHEMA_VERSION


CURRENT_PROCESSING_CONTRACT = ProcessingContract()
