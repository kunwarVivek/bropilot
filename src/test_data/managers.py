"""
Test Data Management Managers

High-level managers for test data operations.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .models import TestDataSet, TestDataRecord, DataScope, DataType, DataSource
from src.infrastructure.logging.logger import StructuredLogger


class TestDataManager:
    """Manager for test data operations."""
    
    def __init__(self, storage_path: str = "test_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = StructuredLogger("test_data_manager")
        
        # In-memory storage for demo (in production, use database)
        self.data_sets: Dict[str, TestDataSet] = {}
        
    async def create_data_set(
        self,
        name: str,
        description: str,
        data_type: str,
        scope: DataScope = DataScope.GLOBAL,
        environment: str = "default",
        **kwargs
    ) -> TestDataSet:
        """Create a new test data set."""
        try:
            data_set = TestDataSet(
                name=name,
                description=description,
                data_type=DataType(data_type) if isinstance(data_type, str) else data_type,
                scope=scope,
                environment=environment,
                **kwargs
            )
            
            # Store data set
            self.data_sets[data_set.id] = data_set
            await self._save_data_set(data_set)
            
            self.logger.info(
                "Test data set created",
                data_set_id=data_set.id,
                name=name,
                data_type=data_type,
                scope=scope.value
            )
            
            return data_set
            
        except Exception as e:
            self.logger.error(
                "Failed to create test data set",
                error=str(e),
                name=name,
                data_type=data_type
            )
            raise
    
    async def get_data_set(self, data_set_id: str) -> Optional[TestDataSet]:
        """Get test data set by ID."""
        if data_set_id in self.data_sets:
            return self.data_sets[data_set_id]
        
        # Try to load from storage
        return await self._load_data_set(data_set_id)
    
    async def generate_data(
        self,
        data_set_id: str,
        count: int,
        generator_type: str,
        **kwargs
    ) -> bool:
        """Generate test data for a data set."""
        try:
            data_set = await self.get_data_set(data_set_id)
            if not data_set:
                raise ValueError(f"Data set {data_set_id} not found")
            
            # Mock data generation for demo
            generated_records = await self._mock_generate_data(
                count, generator_type, **kwargs
            )
            
            # Add records to data set
            for record in generated_records:
                data_set.add_record(record)
            
            # Save updated data set
            await self._save_data_set(data_set)
            
            self.logger.info(
                "Test data generated",
                data_set_id=data_set_id,
                count=count,
                generator_type=generator_type
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to generate test data",
                error=str(e),
                data_set_id=data_set_id,
                count=count,
                generator_type=generator_type
            )
            return False
    
    async def get_data(
        self,
        data_set_id: str,
        criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get test data from a data set."""
        try:
            data_set = await self.get_data_set(data_set_id)
            if not data_set:
                return None
            
            if criteria:
                record = data_set.get_record_by_criteria(criteria)
            else:
                record = data_set.get_random_record()
            
            if record:
                return record.data
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get test data",
                error=str(e),
                data_set_id=data_set_id,
                criteria=criteria
            )
            return None
    
    async def _mock_generate_data(
        self,
        count: int,
        generator_type: str,
        **kwargs
    ) -> List[TestDataRecord]:
        """Mock data generation for demo purposes."""
        records = []
        include_fields = kwargs.get("include_fields", [])
        
        for i in range(count):
            if generator_type == "person":
                data = {
                    "username": f"user_{i:03d}",
                    "email": f"user{i:03d}@example.com",
                    "password": f"password{i:03d}",
                    "first_name": f"FirstName{i:03d}",
                    "last_name": f"LastName{i:03d}",
                    "age": 20 + (i % 50),
                    "phone": f"+1-555-{i:04d}"
                }
            elif generator_type == "company":
                data = {
                    "company_name": f"Company {i:03d} Inc",
                    "email": f"contact{i:03d}@company{i:03d}.com",
                    "phone": f"+1-555-{i:04d}",
                    "address": f"{i:03d} Business St",
                    "industry": ["Technology", "Finance", "Healthcare", "Retail"][i % 4]
                }
            elif generator_type == "product":
                data = {
                    "name": f"Product {i:03d}",
                    "description": f"Description for product {i:03d}",
                    "price": round(10.0 + (i * 5.99), 2),
                    "category": ["Electronics", "Clothing", "Books", "Home"][i % 4],
                    "sku": f"SKU-{i:06d}",
                    "in_stock": i % 3 != 0  # 2/3 in stock
                }
            else:
                data = {
                    "id": i,
                    "value": f"generated_value_{i:03d}",
                    "type": generator_type
                }
            
            # Filter fields if specified
            if include_fields:
                data = {k: v for k, v in data.items() if k in include_fields}
            
            record = TestDataRecord(
                data=data,
                data_type=DataType.PERSON if generator_type == "person" else DataType.CUSTOM,
                source=DataSource.GENERATED
            )
            records.append(record)
        
        return records
    
    async def _save_data_set(self, data_set: TestDataSet) -> None:
        """Save data set to storage."""
        file_path = self.storage_path / f"{data_set.id}.json"
        
        import json
        with open(file_path, 'w') as f:
            json.dump(data_set.to_dict(), f, indent=2, default=str)
    
    async def _load_data_set(self, data_set_id: str) -> Optional[TestDataSet]:
        """Load data set from storage."""
        file_path = self.storage_path / f"{data_set_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert back to TestDataSet object
            data_set = self._dict_to_data_set(data)
            self.data_sets[data_set_id] = data_set
            return data_set
            
        except Exception as e:
            self.logger.error(
                "Failed to load data set",
                error=str(e),
                data_set_id=data_set_id
            )
            return None
    
    def _dict_to_data_set(self, data: Dict[str, Any]) -> TestDataSet:
        """Convert dictionary to TestDataSet object."""
        # Convert records
        records = []
        for record_data in data.get("records", []):
            record = TestDataRecord(
                id=record_data.get("id", ""),
                data=record_data.get("data", {}),
                data_type=DataType(record_data.get("data_type", "custom")),
                source=DataSource(record_data.get("source", "manual")),
                tags=record_data.get("tags", []),
                labels=record_data.get("labels", {}),
                is_masked=record_data.get("is_masked", False),
                usage_count=record_data.get("usage_count", 0),
                created_by=record_data.get("created_by", "system")
            )
            
            # Convert timestamps
            if record_data.get("created_at"):
                record.created_at = datetime.fromisoformat(record_data["created_at"])
            if record_data.get("updated_at"):
                record.updated_at = datetime.fromisoformat(record_data["updated_at"])
            if record_data.get("last_used"):
                record.last_used = datetime.fromisoformat(record_data["last_used"])
            
            records.append(record)
        
        # Convert timestamps
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        last_refresh = None
        
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_refresh"):
            last_refresh = datetime.fromisoformat(data["last_refresh"])
        
        data_set = TestDataSet(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            records=records,
            schema=data.get("schema", {}),
            scope=DataScope(data.get("scope", "global")),
            environment=data.get("environment", "default"),
            data_type=DataType(data.get("data_type", "custom")),
            source=DataSource(data.get("source", "manual")),
            auto_refresh=data.get("auto_refresh", False),
            refresh_interval=data.get("refresh_interval", 3600),
            max_records=data.get("max_records"),
            auto_cleanup=data.get("auto_cleanup", False),
            retention_days=data.get("retention_days"),
            masking_enabled=data.get("masking_enabled", False),
            tags=data.get("tags", []),
            labels=data.get("labels", {}),
            total_records=data.get("total_records", 0),
            used_records=data.get("used_records", 0),
            last_refresh=last_refresh,
            created_at=created_at,
            updated_at=updated_at,
            created_by=data.get("created_by", "system"),
            version=data.get("version", 1)
        )
        
        return data_set


class DataSetManager:
    """Manager for data set operations."""
    
    def __init__(self, test_data_manager: TestDataManager):
        self.test_data_manager = test_data_manager
        self.logger = StructuredLogger("data_set_manager")
    
    async def create_data_set_from_template(
        self,
        template_name: str,
        name: str,
        description: str,
        **kwargs
    ) -> TestDataSet:
        """Create data set from predefined template."""
        templates = {
            "user_accounts": {
                "data_type": "person",
                "schema": {
                    "username": "string",
                    "email": "email",
                    "password": "string",
                    "first_name": "string",
                    "last_name": "string"
                }
            },
            "products": {
                "data_type": "product",
                "schema": {
                    "name": "string",
                    "description": "text",
                    "price": "decimal",
                    "category": "string",
                    "sku": "string"
                }
            },
            "companies": {
                "data_type": "company",
                "schema": {
                    "company_name": "string",
                    "email": "email",
                    "phone": "phone",
                    "address": "string"
                }
            }
        }
        
        if template_name not in templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = templates[template_name]
        
        return await self.test_data_manager.create_data_set(
            name=name,
            description=description,
            data_type=template["data_type"],
            schema=template["schema"],
            **kwargs
        )


class DataGenerationManager:
    """Manager for data generation operations."""
    
    def __init__(self, test_data_manager: TestDataManager):
        self.test_data_manager = test_data_manager
        self.logger = StructuredLogger("data_generation_manager")
    
    async def bulk_generate_data(
        self,
        data_set_configs: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Generate data for multiple data sets."""
        results = {}
        
        for config in data_set_configs:
            data_set_id = config.get("data_set_id")
            count = config.get("count", 10)
            generator_type = config.get("generator_type", "custom")
            
            try:
                success = await self.test_data_manager.generate_data(
                    data_set_id=data_set_id,
                    count=count,
                    generator_type=generator_type,
                    **config.get("generator_options", {})
                )
                results[data_set_id] = success
                
            except Exception as e:
                self.logger.error(
                    "Failed to generate data for data set",
                    error=str(e),
                    data_set_id=data_set_id
                )
                results[data_set_id] = False
        
        return results
    
    async def refresh_data_sets(
        self,
        scope: Optional[DataScope] = None,
        environment: Optional[str] = None
    ) -> int:
        """Refresh data sets that need updating."""
        # This would implement auto-refresh logic
        # For now, return 0 as a placeholder
        return 0
