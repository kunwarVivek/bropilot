"""
Test Data Management Module

Comprehensive test data management for browser automation testing.
"""

from .test_data_manager import TestDataManager, TestDataSet, DataScope
from .data_generators import (
    PersonDataGenerator, 
    CompanyDataGenerator, 
    WebFormDataGenerator,
    APIDataGenerator
)
from .data_providers import (
    DatabaseDataProvider,
    FileDataProvider, 
    APIDataProvider,
    DynamicDataProvider
)
from .data_masking import DataMasker, MaskingStrategy
from .data_validation import TestDataValidator

__all__ = [
    "TestDataManager",
    "TestDataSet", 
    "DataScope",
    "PersonDataGenerator",
    "CompanyDataGenerator", 
    "WebFormDataGenerator",
    "APIDataGenerator",
    "DatabaseDataProvider",
    "FileDataProvider",
    "APIDataProvider", 
    "DynamicDataProvider",
    "DataMasker",
    "MaskingStrategy",
    "TestDataValidator"
]
