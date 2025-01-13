import pytest
from celery.result import AsyncResult
from celery import shared_task
from time import sleep

# Example task for testing
@shared_task
def add(x, y):
    return x + y

def test_celery_task_sync(celery_app):
    """Test task execution synchronously"""
    # Execute task synchronously
    result = add.apply(args=[4, 4])
    assert result.get() == 8

# TODO: Fix this test
# def test_celery_task_async(celery_app):
#     """Test task execution asynchronously"""
#     # Execute task asynchronously
#     task = add.delay(4, 4)
#     assert isinstance(task, AsyncResult)
    
#     # Wait for result (with timeout)
#     result = None
#     for _ in range(5):  # 5 second timeout
#         if task.ready():
#             result = task.get()
#             break
#         sleep(1)
    
#     assert result == 8

# def test_task_retry(celery_app):
#     """Test task retry mechanism"""
#     @shared_task(bind=True, max_retries=3)
#     def failing_task(self):
#         if self.request.retries < 2:  # Fail twice, succeed on third try
#             raise ValueError("Intentional failure")
#         return "Success"

#     result = failing_task.apply()
#     assert result.get() == "Success"

def test_task_error_handling(celery_app):
    """Test task error handling"""
    @shared_task
    def error_task():
        raise ValueError("Expected error")

    result = error_task.apply()
    with pytest.raises(ValueError, match="Expected error"):
        result.get() 