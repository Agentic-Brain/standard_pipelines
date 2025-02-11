import os
import pytest
from flask import url_for
from datetime import datetime
from standard_pipelines.api.google.gmail_services import GmailAPIManager
from standard_pipelines.api.google.models import GoogleCredentials
from standard_pipelines.data_flow.models import Client
from standard_pipelines.extensions import db
from standard_pipelines.auth.models import User
from tests.test_auth import create_client_util
from flask_login import login_user
from tests.test_persistent_db import persistent_db

@pytest.fixture
def gmail_test_config(app, persistent_db):
    """Setup test configuration for Gmail API tests"""

    # Get the client from persistent_db
    client = Client.query.get(persistent_db['client_id'])
    user = User.query.get(persistent_db['user_id'])
    
    return {
        'client': client,
        'user': user,
        'test_recipient': app.config['GMAIL_TEST_RECIPIENT']
    }

def test_gmail_send_email(app, gmail_test_config):
    """Test that Gmail API credentials are properly loaded and working"""
    
    # Create Google credentials for the test client
    credentials = GoogleCredentials.query.filter_by(client_id=gmail_test_config['client'].id).first()

    try:
        # Initialize Gmail API with credentials
        api_config = {
            'refresh_token': credentials.refresh_token
        }
        gmail_api = GmailAPIManager(api_config)
        gmail_api.send_email(gmail_test_config['test_email'], "Test Email", "This is an integration test email from the Gmail API tests.")
        
        # Test sending an email
        subject = f"Test Email {datetime.now().isoformat()}"
        body = "This is an integration test email from the Gmail API tests."
        response = gmail_api.send_email(
            gmail_test_config['test_recipient'],
            subject,
            body
        )
        
        assert 'message' in response, "No message in response"
        assert response['message'] == 'Email sent successfully', "Email send failed"
        assert 'message_id' in response, "No message ID in response"
        
    except Exception as e:
        pytest.fail(f"Failed to use Gmail API: {str(e)}")

# def test_oauth_flow(client, app):
#     """Test the complete OAuth flow for Gmail integration"""
#     # Check if OAuth credentials exist
#     assert 'TESTING_GOOGLE_CLIENT_ID' in os.environ, "Google OAuth client ID not found"
#     assert 'TESTING_GOOGLE_CLIENT_SECRET' in os.environ, "Google OAuth client secret not found"
    
#     # Create a test client
#     test_client = create_client_util()
    
#     try:
#         # Test initiating OAuth flow
#         response = client.get(url_for('api.login_google'))
#         assert response.status_code == 302, "OAuth initiation failed"
#         assert 'accounts.google.com' in response.headers['Location'], "Not redirected to Google"
        
#         # Note: Full OAuth flow can't be tested automatically as it requires user interaction
#         # Instead, verify we can create and use credentials
#         credentials = GoogleCredentials(
#             client_id=test_client.id,
#             refresh_token=os.environ['TESTING_GOOGLE_REFRESH_TOKEN']
#         )
#         credentials.client = test_client
#         credentials.save()
        
#         # Verify credentials were saved
#         saved_creds = GoogleCredentials.query.filter_by(client_id=test_client.id).first()
#         assert saved_creds is not None, "Credentials not saved"
#         assert saved_creds.refresh_token == os.environ['TESTING_GOOGLE_REFRESH_TOKEN']
        
#     except Exception as e:
#         pytest.fail(f"OAuth flow test failed: {str(e)}")
#     finally:
#         # Cleanup
#         if credentials:
#             credentials.delete()
#         test_client.delete()

# def test_gmail_token_refresh(app):
#     """Test Gmail API token refresh functionality"""
#     # Create test client and credentials
#     client = create_client_util()
#     credentials = GoogleCredentials(
#         client_id=client.id,
#         refresh_token=os.environ['TESTING_GOOGLE_REFRESH_TOKEN']
#     )
#     credentials.client = client
#     credentials.save()
    
#     try:
#         # Initialize Gmail API
#         api_config = {
#             'refresh_token': os.environ['TESTING_GOOGLE_REFRESH_TOKEN']
#         }
#         gmail_api = GmailAPIManager(api_config)
        
#         # Force a token refresh
#         gmail_api.refresh_token
        
#         # Verify we can still use the API after refresh
#         response = gmail_api.send_email(
#             os.environ['TESTING_GMAIL_TEST_EMAIL'],
#             "Test After Token Refresh",
#             "This email confirms the token refresh worked."
#         )
        
#         assert response['message'] == 'Email sent successfully', "Email failed after token refresh"
        
#     except Exception as e:
#         pytest.fail(f"Token refresh test failed: {str(e)}")
#     finally:
#         # Cleanup
#         credentials.delete()
#         client.delete()

# def test_gmail_oauth_and_send(client, app, gmail_test_config):
#     """Test complete Gmail flow: OAuth -> Save Credentials -> Send Email"""
#     test_client = gmail_test_config['client']
#     test_user = gmail_test_config['user']
    
#     with app.test_request_context():
#         # Login the test user
#         login_user(test_user)
        
#         try:
#             # 1. Start OAuth Flow
#             response = client.get(url_for('api.login_google'))
#             assert response.status_code == 302, "OAuth initiation failed"
#             assert 'accounts.google.com' in response.headers['Location'], "Not redirected to Google"
            
#             # 2. Simulate OAuth callback by creating credentials
#             # (since we can't automate the actual Google consent screen)
#             credentials = GoogleCredentials(
#                 client_id=test_client.id,
#                 refresh_token=os.environ['TESTING_GOOGLE_REFRESH_TOKEN']
#             )
#             credentials.client = test_client
#             credentials.save()
            
#             # Verify credentials were saved
#             saved_creds = GoogleCredentials.query.filter_by(client_id=test_client.id).first()
#             assert saved_creds is not None, "Credentials not saved"
            
#             # 3. Test sending an email using the saved credentials
#             api_config = {
#                 'refresh_token': saved_creds.refresh_token
#             }
#             gmail_api = GmailAPIManager(api_config)
            
#             subject = f"Integration Test Email {datetime.now().isoformat()}"
#             body = "This is a complete integration test email from the Gmail API tests."
#             response = gmail_api.send_email(
#                 gmail_test_config['test_email'],
#                 subject,
#                 body
#             )
            
#             assert 'message' in response, "No message in response"
#             assert response['message'] == 'Email sent successfully', "Email send failed"
#             assert 'message_id' in response, "No message ID in response"
            
#         except Exception as e:
#             pytest.fail(f"Gmail integration test failed: {str(e)}")
#         finally:
#             # Cleanup only the credentials, leave persistent_db items
#             if 'credentials' in locals():
#                 credentials.delete()

# def test_gmail_token_refresh_flow(app, gmail_test_config):
#     """Test Gmail API token refresh with persistent client"""
#     test_client = gmail_test_config['client']
    
#     try:
#         # Create credentials for the persistent client
#         credentials = GoogleCredentials(
#             client_id=test_client.id,
#             refresh_token=os.environ['TESTING_GOOGLE_REFRESH_TOKEN']
#         )
#         credentials.client = test_client
#         credentials.save()
        
#         # Initialize Gmail API
#         api_config = {
#             'refresh_token': credentials.refresh_token
#         }
#         gmail_api = GmailAPIManager(api_config)
        
#         # Force a token refresh
#         gmail_api.refresh_token
        
#         # Verify API still works after refresh
#         response = gmail_api.send_email(
#             gmail_test_config['test_email'],
#             f"Token Refresh Test {datetime.now().isoformat()}",
#             "This email confirms the token refresh worked with persistent client."
#         )
        
#         assert response['message'] == 'Email sent successfully', "Email failed after token refresh"
        
#     except Exception as e:
#         pytest.fail(f"Token refresh test failed: {str(e)}")
#     finally:
#         if 'credentials' in locals():
#             credentials.delete()
