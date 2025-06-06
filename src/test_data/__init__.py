"""
Test Data Management System

Comprehensive test data management for LLM-powered browser automation testing.
Provides data generation, management, masking, and validation capabilities.
"""

from .models import (
    TestDataSet,
    TestDataRecord,
    DataScope,
    DataType,
    DataSource,
    DataMaskingRule
)

from .managers import (
    TestDataManager,
    DataSetManager,
    DataGenerationManager
)

from .generators import (
    PersonDataGenerator,
    CompanyDataGenerator,
    ProductDataGenerator,
    CustomDataGenerator
)

# TODO: Implement these modules
# from .providers import (
#     DatabaseDataProvider,
#     FileDataProvider,
#     APIDataProvider,
#     DynamicDataProvider
# )

# from .masking import (
#     DataMasker,
#     MaskingStrategy,
#     PIIMasker
# )

# from .validation import (
#     TestDataValidator,
#     DataQualityChecker
# )

__all__ = [
    # Models
    "TestDataSet",
    "TestDataRecord",
    "DataScope",
    "DataType",
    "DataSource",
    "DataMaskingRule",

    # Managers
    "TestDataManager",
    "DataSetManager",
    "DataGenerationManager",

    # Generators
    "PersonDataGenerator",
    "CompanyDataGenerator",
    "ProductDataGenerator",
    "CustomDataGenerator",

    # TODO: Add when implemented
    # "DatabaseDataProvider",
    # "FileDataProvider",
    # "APIDataProvider",
    # "DynamicDataProvider",
    # "DataMasker",
    # "MaskingStrategy",
    # "PIIMasker",
    # "TestDataValidator",
    # "DataQualityChecker"
]
