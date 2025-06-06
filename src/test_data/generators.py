"""
Test Data Generators

Generators for creating test data of various types.
"""

import random
import string
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

from .models import TestDataRecord, DataType, DataSource
from src.infrastructure.logging.logger import StructuredLogger


class PersonDataGenerator:
    """Generator for person/user test data."""
    
    def __init__(self):
        self.logger = StructuredLogger("person_data_generator")
        
        self.first_names = [
            "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
            "James", "Maria", "William", "Jennifer", "Richard", "Linda", "Charles",
            "Patricia", "Joseph", "Barbara", "Thomas", "Elizabeth"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
            "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
        ]
        
        self.domains = [
            "example.com", "test.org", "demo.net", "sample.io", "mock.co"
        ]
    
    async def generate_records(
        self,
        count: int,
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> List[TestDataRecord]:
        """Generate person test data records."""
        records = []
        
        for i in range(count):
            data = self._generate_person_data(i, include_fields, **kwargs)
            
            record = TestDataRecord(
                data=data,
                data_type=DataType.PERSON,
                source=DataSource.GENERATED,
                tags=["person", "user"],
                created_by="person_data_generator"
            )
            
            records.append(record)
        
        self.logger.info(
            "Person data records generated",
            count=count,
            include_fields=include_fields
        )
        
        return records
    
    def _generate_person_data(
        self,
        index: int,
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate data for a single person."""
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        
        data = {
            "id": f"user_{index:04d}",
            "username": f"{first_name.lower()}.{last_name.lower()}{index:02d}",
            "email": f"{first_name.lower()}.{last_name.lower()}{index:02d}@{random.choice(self.domains)}",
            "password": self._generate_password(),
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "age": random.randint(18, 80),
            "phone": self._generate_phone_number(),
            "address": self._generate_address(index),
            "date_of_birth": self._generate_date_of_birth(),
            "gender": random.choice(["male", "female", "other"]),
            "occupation": random.choice([
                "Engineer", "Teacher", "Doctor", "Artist", "Manager", "Developer",
                "Designer", "Analyst", "Consultant", "Writer"
            ]),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": random.choice([True, True, True, False])  # 75% active
        }
        
        # Filter fields if specified
        if include_fields:
            data = {k: v for k, v in data.items() if k in include_fields}
        
        return data
    
    def _generate_password(self) -> str:
        """Generate a secure password."""
        length = random.randint(8, 16)
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _generate_phone_number(self) -> str:
        """Generate a phone number."""
        area_code = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        return f"+1-{area_code}-{exchange}-{number}"
    
    def _generate_address(self, index: int) -> Dict[str, str]:
        """Generate an address."""
        street_names = [
            "Main St", "Oak Ave", "Pine Rd", "Elm Dr", "Maple Ln",
            "Cedar Blvd", "Park Ave", "First St", "Second St", "Broadway"
        ]
        
        cities = [
            "Springfield", "Franklin", "Georgetown", "Madison", "Washington",
            "Arlington", "Richmond", "Fairview", "Riverside", "Greenwood"
        ]
        
        states = [
            "CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"
        ]
        
        return {
            "street": f"{random.randint(1, 9999)} {random.choice(street_names)}",
            "city": random.choice(cities),
            "state": random.choice(states),
            "zip_code": f"{random.randint(10000, 99999)}",
            "country": "USA"
        }
    
    def _generate_date_of_birth(self) -> str:
        """Generate a date of birth."""
        start_date = datetime.now() - timedelta(days=80*365)
        end_date = datetime.now() - timedelta(days=18*365)
        
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        
        birth_date = start_date + timedelta(days=random_days)
        return birth_date.strftime("%Y-%m-%d")


class CompanyDataGenerator:
    """Generator for company/organization test data."""
    
    def __init__(self):
        self.logger = StructuredLogger("company_data_generator")
        
        self.company_types = [
            "Inc", "LLC", "Corp", "Ltd", "Co", "Group", "Solutions", "Systems",
            "Technologies", "Enterprises", "Industries", "Services"
        ]
        
        self.business_words = [
            "Global", "Advanced", "Premier", "Elite", "Dynamic", "Innovative",
            "Strategic", "Professional", "Creative", "Digital", "Smart", "Future"
        ]
        
        self.industries = [
            "Technology", "Healthcare", "Finance", "Education", "Retail",
            "Manufacturing", "Consulting", "Media", "Transportation", "Energy"
        ]
    
    async def generate_records(
        self,
        count: int,
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> List[TestDataRecord]:
        """Generate company test data records."""
        records = []
        
        for i in range(count):
            data = self._generate_company_data(i, include_fields, **kwargs)
            
            record = TestDataRecord(
                data=data,
                data_type=DataType.COMPANY,
                source=DataSource.GENERATED,
                tags=["company", "organization"],
                created_by="company_data_generator"
            )
            
            records.append(record)
        
        self.logger.info(
            "Company data records generated",
            count=count,
            include_fields=include_fields
        )
        
        return records
    
    def _generate_company_data(
        self,
        index: int,
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate data for a single company."""
        business_word = random.choice(self.business_words)
        company_type = random.choice(self.company_types)
        
        company_name = f"{business_word} {company_type}"
        
        data = {
            "id": f"company_{index:04d}",
            "company_name": company_name,
            "legal_name": f"{company_name} {random.choice(['Inc', 'LLC', 'Corp'])}",
            "email": f"contact@{company_name.lower().replace(' ', '')}.com",
            "website": f"https://www.{company_name.lower().replace(' ', '')}.com",
            "phone": self._generate_business_phone(),
            "industry": random.choice(self.industries),
            "employee_count": random.choice([
                "1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"
            ]),
            "founded_year": random.randint(1950, 2020),
            "revenue": random.choice([
                "< $1M", "$1M - $10M", "$10M - $50M", "$50M - $100M", "> $100M"
            ]),
            "address": self._generate_business_address(index),
            "description": f"Leading {random.choice(self.industries).lower()} company providing innovative solutions.",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": random.choice([True, True, True, False])  # 75% active
        }
        
        # Filter fields if specified
        if include_fields:
            data = {k: v for k, v in data.items() if k in include_fields}
        
        return data
    
    def _generate_business_phone(self) -> str:
        """Generate a business phone number."""
        area_code = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        return f"+1-{area_code}-{exchange}-{number}"
    
    def _generate_business_address(self, index: int) -> Dict[str, str]:
        """Generate a business address."""
        street_types = ["St", "Ave", "Blvd", "Dr", "Ln", "Rd", "Plaza", "Way"]
        business_streets = [
            "Business", "Corporate", "Commerce", "Industrial", "Technology",
            "Innovation", "Enterprise", "Professional", "Executive", "Trade"
        ]
        
        cities = [
            "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
            "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"
        ]
        
        states = [
            "CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"
        ]
        
        return {
            "street": f"{random.randint(100, 9999)} {random.choice(business_streets)} {random.choice(street_types)}",
            "suite": f"Suite {random.randint(100, 999)}" if random.choice([True, False]) else "",
            "city": random.choice(cities),
            "state": random.choice(states),
            "zip_code": f"{random.randint(10000, 99999)}",
            "country": "USA"
        }


class ProductDataGenerator:
    """Generator for product test data."""
    
    def __init__(self):
        self.logger = StructuredLogger("product_data_generator")
        
        self.product_adjectives = [
            "Premium", "Deluxe", "Professional", "Advanced", "Standard",
            "Basic", "Ultimate", "Elite", "Pro", "Classic", "Modern", "Smart"
        ]
        
        self.product_types = [
            "Widget", "Device", "Tool", "System", "Solution", "Kit",
            "Package", "Bundle", "Set", "Collection", "Series", "Model"
        ]
        
        self.categories = [
            "Electronics", "Clothing", "Books", "Home & Garden", "Sports",
            "Toys", "Health", "Beauty", "Automotive", "Office Supplies"
        ]
    
    async def generate_records(
        self,
        count: int,
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> List[TestDataRecord]:
        """Generate product test data records."""
        records = []
        
        for i in range(count):
            data = self._generate_product_data(i, include_fields, **kwargs)
            
            record = TestDataRecord(
                data=data,
                data_type=DataType.PRODUCT,
                source=DataSource.GENERATED,
                tags=["product", "inventory"],
                created_by="product_data_generator"
            )
            
            records.append(record)
        
        self.logger.info(
            "Product data records generated",
            count=count,
            include_fields=include_fields
        )
        
        return records
    
    def _generate_product_data(
        self,
        index: int,
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate data for a single product."""
        adjective = random.choice(self.product_adjectives)
        product_type = random.choice(self.product_types)
        
        product_name = f"{adjective} {product_type} {index:03d}"
        
        base_price = random.uniform(10.0, 1000.0)
        
        data = {
            "id": f"product_{index:04d}",
            "sku": f"SKU-{index:06d}",
            "name": product_name,
            "description": f"High-quality {product_name.lower()} designed for professional use.",
            "category": random.choice(self.categories),
            "price": round(base_price, 2),
            "sale_price": round(base_price * random.uniform(0.7, 0.9), 2) if random.choice([True, False]) else None,
            "cost": round(base_price * random.uniform(0.3, 0.6), 2),
            "weight": round(random.uniform(0.1, 50.0), 2),
            "dimensions": {
                "length": round(random.uniform(1.0, 100.0), 1),
                "width": round(random.uniform(1.0, 100.0), 1),
                "height": round(random.uniform(1.0, 100.0), 1),
                "unit": "cm"
            },
            "stock_quantity": random.randint(0, 1000),
            "min_stock_level": random.randint(5, 50),
            "max_stock_level": random.randint(100, 500),
            "is_active": random.choice([True, True, True, False]),  # 75% active
            "is_featured": random.choice([True, False, False, False]),  # 25% featured
            "rating": round(random.uniform(1.0, 5.0), 1),
            "review_count": random.randint(0, 1000),
            "tags": random.sample([
                "bestseller", "new", "sale", "premium", "eco-friendly",
                "limited-edition", "popular", "recommended"
            ], k=random.randint(1, 3)),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Filter fields if specified
        if include_fields:
            data = {k: v for k, v in data.items() if k in include_fields}
        
        return data


class CustomDataGenerator:
    """Generator for custom test data based on schema."""
    
    def __init__(self):
        self.logger = StructuredLogger("custom_data_generator")
    
    async def generate_records(
        self,
        count: int,
        schema: Dict[str, str],
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> List[TestDataRecord]:
        """Generate custom test data records based on schema."""
        records = []
        
        for i in range(count):
            data = self._generate_custom_data(i, schema, include_fields, **kwargs)
            
            record = TestDataRecord(
                data=data,
                data_type=DataType.CUSTOM,
                source=DataSource.GENERATED,
                tags=["custom"],
                created_by="custom_data_generator"
            )
            
            records.append(record)
        
        self.logger.info(
            "Custom data records generated",
            count=count,
            schema_fields=list(schema.keys()),
            include_fields=include_fields
        )
        
        return records
    
    def _generate_custom_data(
        self,
        index: int,
        schema: Dict[str, str],
        include_fields: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate custom data based on schema."""
        data = {}
        
        for field_name, field_type in schema.items():
            if include_fields and field_name not in include_fields:
                continue
            
            data[field_name] = self._generate_field_value(field_name, field_type, index)
        
        return data
    
    def _generate_field_value(self, field_name: str, field_type: str, index: int) -> Any:
        """Generate value for a specific field type."""
        field_type = field_type.lower()
        
        if field_type in ["string", "str", "text"]:
            return f"{field_name}_{index:04d}"
        elif field_type in ["int", "integer", "number"]:
            return random.randint(1, 1000)
        elif field_type in ["float", "decimal", "double"]:
            return round(random.uniform(1.0, 1000.0), 2)
        elif field_type in ["bool", "boolean"]:
            return random.choice([True, False])
        elif field_type in ["email", "email_address"]:
            return f"{field_name}{index:03d}@example.com"
        elif field_type in ["phone", "phone_number"]:
            return f"+1-555-{index:04d}"
        elif field_type in ["date", "datetime"]:
            return datetime.now(timezone.utc).isoformat()
        elif field_type in ["url", "website"]:
            return f"https://example{index:03d}.com"
        else:
            return f"{field_name}_value_{index:04d}"
