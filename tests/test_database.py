import pytest
from standard_pipelines.extensions import db
from standard_pipelines.database.models import BaseMixin
import uuid
from datetime import datetime
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

# Test model that implements BaseMixin which includes timestamp fields
class SampleModel(BaseMixin):
    __tablename__ = 'sample_models'
    
    name: Mapped[str] = mapped_column(String(50))
    
    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)

@pytest.fixture(scope="module")
def db_session(app):
    """Creates a new database session for each test"""
    with app.app_context():
        yield db.session
        db.session.rollback()

@pytest.fixture(autouse=True)
def cleanup(db_session):
    """Cleanup after each test"""
    yield
    db_session.query(SampleModel).delete()
    db_session.commit()

def test_base_mixin(db_session):
    # Test creating an instance with BaseMixin
    test_obj = SampleModel(name="test")
    test_obj.save()
    
    # Verify ID was generated
    assert isinstance(test_obj.id, uuid.UUID)
    
    # Test retrieving
    retrieved = db_session.get(SampleModel, test_obj.id)
    assert retrieved.name == "test"
    
    # Test deletion
    test_obj.delete()
    assert db_session.get(SampleModel, test_obj.id) is None

def test_timestamps(db_session):
    # Test timestamp functionality from BaseMixin
    test_obj = SampleModel(name="timestamp_test")
    test_obj.save()
    
    # Verify timestamps were set
    assert isinstance(test_obj.created_at, datetime)
    assert isinstance(test_obj.modified_at, datetime)
    
    # Test modification timestamp updates
    original_modified = test_obj.modified_at
    test_obj.name = "updated"
    db_session.commit()
    
    assert test_obj.modified_at > original_modified

def test_model_relationships(db_session):
    # Create multiple objects and test basic querying
    obj1 = SampleModel(name="first")
    obj2 = SampleModel(name="second")
    obj1.save()
    obj2.save()
    
    # Test basic querying
    results = SampleModel.query.all()
    assert len(results) == 2
    assert any(obj.name == "first" for obj in results)
    assert any(obj.name == "second" for obj in results)

def test_bulk_operations(db_session):
    # Test bulk insert
    objects = [
        SampleModel(name=f"bulk_{i}")
        for i in range(5)
    ]
    db_session.bulk_save_objects(objects)
    db_session.commit()
    
    # Verify bulk insert
    count = SampleModel.query.count()
    assert count == 5
    
    # Test bulk delete
    SampleModel.query.delete()
    db_session.commit()
    
    assert SampleModel.query.count() == 0
