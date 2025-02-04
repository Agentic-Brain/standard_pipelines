import pytest
from flask import url_for
from werkzeug.exceptions import NotFound, HTTPException
from sqlalchemy.exc import SQLAlchemyError
import json
import urllib.parse
from unittest.mock import patch, MagicMock, ANY



GET_CLIENT = 'standard_pipelines.api.gmail.routes.Client'
GET_FLOW = 'standard_pipelines.api.gmail.routes.get_flow'
GET_LOGS = 'standard_pipelines.api.gmail.routes.current_app.logger'
GET_GMAIL_CREDENTIALS = 'standard_pipelines.api.gmail.routes.GmailCredentials'
GET_GMAIL_SERVICE = 'standard_pipelines.api.gmail.routes.GmailService'

#======================================================================#
#=========================== Routes Tests =============================#

#========== Authorize Route ==========#
@patch(GET_LOGS)
@patch(GET_CLIENT)
@patch(GET_FLOW)
def test_authorize_route_success(mock_flow, mock_client, mock_logger, client):
    """Test the /authorize/<client_id> route for correct redirection."""
    auth_url = 'http://mock_authorization_url'
    state = 'mock_state'
    client_id = 'mock_client_id'

    # Mock the OAuth flow
    mock_flow_instance = MagicMock()
    mock_flow_instance.authorization_url.return_value = (auth_url, state)
    mock_flow.return_value = mock_flow_instance
    # Mock the client retrieval
    mock_client.query.get_or_404.return_value = MagicMock(id=client_id)

    with client.application.test_request_context():
        # Simulate a request to the authorize route
        response = client.get(url_for('gmail.authorize', client_id=client_id))

    assert response.status_code == 302
    assert response.headers['Location'] == auth_url

    with client.session_transaction() as session:
        assert session['state'] == state

    mock_client.query.get_or_404.assert_called_once_with(client_id)

    mock_flow_instance.authorization_url.assert_called_once_with(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=ANY 
    )

@patch(GET_LOGS)
@patch(GET_CLIENT)
@patch(GET_FLOW)
def test_authorize_route_missing_redirect_url(mock_flow, mock_client, mock_logger, client):
    """Test the /authorize/<client_id> route with a missing redirect URL."""
    auth_url = 'http://mock_authorization_url'
    state = 'mock_state'
    client_id = 'mock_client_id'

    mock_flow_instance = MagicMock()
    mock_flow_instance.authorization_url.return_value = (auth_url, state)
    mock_flow.return_value = mock_flow_instance
    mock_client.query.get_or_404.return_value = MagicMock(id=client_id)

    with client.application.test_request_context():
        response = client.get(url_for('gmail.authorize', client_id=client_id))

        assert response.status_code == 302
        assert response.headers['Location'] == auth_url

        with client.session_transaction() as session:
            assert session['state'] == state

        mock_flow_instance.authorization_url.assert_called_once_with(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=ANY  
        )
        # Ensure that the redirect_url is set to default, main.index
        serialized_data = mock_flow_instance.authorization_url.call_args[1]['state']
        decoded_data = json.loads(urllib.parse.unquote(serialized_data))
        expected_redirect_url = url_for('main.index')
        assert decoded_data['redirect_url'] == expected_redirect_url

def test_authorize_route_missing_client_id(client):
    """Test the /authorize/<client_id> route with a missing client_id."""
    response = client.get('/authorize/')
    # Expect a 404 Not Found error because the route requires a client_id
    assert response.status_code == 404

@patch(GET_LOGS)
@patch(GET_CLIENT)
def test_authorize_route_invalid_client_id(mock_client, mock_logger, client):
    """Test the /authorize/<client_id> route with an invalid client_id."""
    client_id = 'invalid_id'
    mock_client.query.get_or_404.side_effect = NotFound(description=f"Client {client_id} not found")
    
    with client.application.test_request_context():
        response = client.get(url_for('gmail.authorize', client_id=client_id))
        assert response.status_code == 302
        assert response.headers['Location'] == url_for('main.index')

    # Verify that the correct error handler was called
    mock_logger.exception.assert_called_with(f"HTTP error during authorization: 404 Not Found: Client {client_id} not found")

@patch(GET_LOGS)
@patch(GET_FLOW)
@patch(GET_CLIENT)
def test_authorize_route_oauth_flow_error(mock_client, mock_flow, mock_logger, client):
    """Test the /authorize/<client_id> route with an error during OAuth flow setup."""
    client_id = 'valid_client_id'
    mock_client.query.get_or_404.return_value = MagicMock(id=client_id)

    exception = HTTPException(description="An unexpected error occurred while creating the OAuth flow")
    exception.code = 500
    mock_flow.side_effect = exception

    with client.application.test_request_context():
        response = client.get(url_for('gmail.authorize', client_id=client_id))
        assert response.status_code == 302
        assert response.headers['Location'] == url_for('main.index')

    mock_logger.exception.assert_called_with("HTTP error during authorization: 500 Internal Server Error: An unexpected error occurred while creating the OAuth flow")

@patch(GET_LOGS)
@patch(GET_FLOW)
@patch(GET_CLIENT)
def test_authorize_route_http_exception_handling(mock_client, mock_flow, mock_logger, client):
    """Test general HTTP exception handling in the /authorize/<client_id> route."""
    client_id = 'valid_client_id'
    mock_client.query.get_or_404.return_value = MagicMock(id=client_id)

    # Simulate a general HTTP exception during the OAuth flow setup
    exception = HTTPException(description="General HTTP error occurred")
    exception.code = 500
    mock_flow.side_effect = exception

    with client.application.test_request_context():
        response = client.get(url_for('gmail.authorize', client_id=client_id))

        assert response.status_code == 302
        assert response.headers['Location'] == url_for('main.index')

        mock_logger.exception.assert_called_with("HTTP error during authorization: 500 Internal Server Error: General HTTP error occurred")

@patch(GET_LOGS)
@patch(GET_FLOW)
@patch(GET_CLIENT)
def test_authorize_route_value_error_handling(mock_client, mock_flow, mock_logger, client):
    """Test value error handling in the /authorize/<client_id> route."""
    client_id = 'valid_client_id'

    mock_client.query.get_or_404.return_value = MagicMock(id=client_id)
    mock_flow.side_effect = ValueError("Invalid data encountered")

    with client.application.test_request_context():
        response = client.get(url_for('gmail.authorize', client_id=client_id))

        assert response.status_code == 302
        assert response.headers['Location'] == url_for('main.index')

        mock_logger.exception.assert_called_with("Value error during authorization: Invalid data encountered")

@patch(GET_LOGS)
@patch(GET_FLOW)
@patch(GET_CLIENT)
def test_authorize_route_unexpected_error_handling(mock_client, mock_flow, mock_logger, client):
    """Test unexpected error handling in the /authorize/<client_id> route."""
    client_id = 'valid_client_id'
    mock_client.query.get_or_404.return_value = MagicMock(id=client_id)
    mock_flow.side_effect = Exception("Unexpected error occurred")

    with client.application.test_request_context():
        response = client.get(url_for('gmail.authorize', client_id=client_id))

        assert response.status_code == 302
        assert response.headers['Location'] == url_for('main.index')

        mock_logger.exception.assert_called_with("Unexpected error during authorization: Unexpected error occurred")

#========== OAuth2 Callback Route ==========#
@patch(GET_LOGS)
@patch(GET_GMAIL_CREDENTIALS)
@patch(GET_FLOW)
@patch(GET_CLIENT)
def test_oauth2callback_new_account_success(mock_client, mock_flow, mock_gmail_credentials, mock_logger, client):
    """Test the /oauth2callback route for handling OAuth callback for a new account."""
    # Create a mock for the OAuth flow
    mock_flow_instance = MagicMock()
    mock_flow_instance.fetch_token.return_value = None

    # Create a mock for the credentials
    mock_credentials = MagicMock(
        token='mock_access_token',
        refresh_token='mock_refresh_token',
        set_expire_time_from_datetime=MagicMock(return_value=None),
        client=MagicMock(),
        save=MagicMock(return_value=None)
    )
    mock_flow_instance.credentials = mock_credentials
    mock_flow.return_value = mock_flow_instance
   
    # Mock the client retrieval
    client_id = 'mock_client_id'
    redirect_url = 'http://testing.com'
    mock_client_instance = MagicMock(id=client_id)
    mock_client.query.get_or_404.return_value = mock_client_instance

    # Mock the GmailCredentials query to simulate no existing credentials
    mock_gmail_credentials.query.filter_by.return_value.first.return_value = None
    mock_gmail_credentials_instance = MagicMock()
    mock_gmail_credentials.return_value = mock_gmail_credentials_instance

    state_data = {'client_id': client_id, 'redirect_url': redirect_url}
    serialized_state = json.dumps(state_data, separators=(',', ':'))
    
    # Simulate a request to the oauth2callback route with the correct state and code
    with client.application.test_request_context():
        with client.session_transaction() as session:
            session['state'] = serialized_state
        response = client.get(url_for('gmail.oauth2callback'), query_string={'state': serialized_state, 'code': 'mock_code'})

    assert response.status_code == 302
    assert response.headers['Location'] == redirect_url

    # Assert fetch_token was called with the correct URL
    mock_flow_instance.fetch_token.assert_called_once_with(
        authorization_response=f'http://localhost/api/gmail/oauth2callback?state={serialized_state}&code=mock_code'
    )

    mock_client.query.get_or_404.assert_called_once_with(client_id)

    # Assert new credentials were created and saved
    mock_gmail_credentials.assert_called_once_with(
        access_token='mock_access_token',
        expire_time='',
        refresh_token='mock_refresh_token',
    )

    # Ensure the instance methods were called
    mock_gmail_credentials_instance.set_expire_time_from_datetime.assert_called_once()
    mock_gmail_credentials_instance.save.assert_called_once()

    mock_logger.info.assert_any_call('Created new credentials for client')
    mock_logger.info.assert_any_call('Client has been successfully authorized')

@patch(GET_LOGS)
@patch(GET_GMAIL_CREDENTIALS)
@patch(GET_FLOW)
@patch(GET_CLIENT)
def test_oauth2callback_existing_account_success(mock_client, mock_flow, mock_gmail_credentials, mock_logger, client):
    """Test the /oauth2callback route for handling OAuth callback for an existing account."""
    # Create a mock for the OAuth flow
    mock_flow_instance = MagicMock()
    mock_flow_instance.fetch_token.return_value = None

    # Create a mock for the credentials
    mock_credentials = MagicMock(
        token='mock_access_token',
        refresh_token='mock_refresh_token',
        set_expire_time_from_datetime=MagicMock(return_value=None),
        client=MagicMock(),
        save=MagicMock(return_value=None)
    )
    mock_flow_instance.credentials = mock_credentials
    mock_flow.return_value = mock_flow_instance
   
    # Mock the client retrieval
    client_id = 'mock_client_id'
    redirect_url = 'http://testing.com'
    mock_client_instance = MagicMock(id=client_id)
    mock_client.query.get_or_404.return_value = mock_client_instance

    # Mock the GmailCredentials query to simulate existing credentials
    existing_credentials = MagicMock()
    mock_gmail_credentials.query.filter_by.return_value.first.return_value = existing_credentials

    state_data = {'client_id': client_id, 'redirect_url': redirect_url}
    serialized_state = json.dumps(state_data, separators=(',', ':'))
    
    # Simulate a request to the oauth2callback route with the correct state and code
    with client.application.test_request_context():
        with client.session_transaction() as session:
            session['state'] = serialized_state
        response = client.get(url_for('gmail.oauth2callback'), query_string={'state': serialized_state, 'code': 'mock_code'})

    assert response.status_code == 302
    assert response.headers['Location'] == redirect_url

    # Assert fetch_token was called with the correct URL
    mock_flow_instance.fetch_token.assert_called_once_with(
        authorization_response=f'http://localhost/api/gmail/oauth2callback?state={serialized_state}&code=mock_code'
    )

    mock_client.query.get_or_404.assert_called_once_with(client_id)

    # Assert existing credentials were updated
    assert existing_credentials.access_token == mock_credentials.token
    assert existing_credentials.refresh_token == mock_credentials.refresh_token
    existing_credentials.set_expire_time_from_datetime.assert_called_once()
    existing_credentials.save.assert_called_once()

    mock_logger.info.assert_any_call('Updated existing credentials for client')
    mock_logger.info.assert_any_call('Client has been successfully authorized')

@patch(GET_LOGS)
@patch(GET_FLOW, return_value=MagicMock())
def test_oauth2callback_missing_state(mock_flow, mock_logger, client):
    """Test that missing state parameter results in an error redirect."""
    with client.application.test_request_context():
        response = client.get(url_for('gmail.oauth2callback'), query_string={'code': 'mock_code'})
        assert response.headers['Location'] == url_for('main.index')
        
    assert response.status_code == 302    
    mock_logger.exception.assert_called_with('State parameter is missing from request from Google')

@patch(GET_LOGS)
@patch(GET_FLOW, return_value=MagicMock())
def test_oauth2callback_invalid_state(mock_flow, mock_logger, client):
    """Test that an invalid state parameter results in an error redirect."""
    redirect_url = 'http://testing.com'
    state_data = {'client_id': 'mock_client_id', 'redirect_url': redirect_url}
    serialized_state = json.dumps(state_data, separators=(',', ':'))

    with client.application.test_request_context():
        with client.session_transaction() as session:
            session['state'] = 'some_other_state'  # Set a different state in the session
        response = client.get(url_for('gmail.oauth2callback'), query_string={'state': serialized_state, 'code': 'mock_code'})
        assert response.headers['Location'] == redirect_url
        
    assert response.status_code == 302
    mock_logger.exception.assert_called_with(f'Invalid state parameter: Start: some_other_state End:{serialized_state}')

@patch(GET_LOGS)
@patch(GET_FLOW, return_value=MagicMock())
def test_oauth2callback_missing_required_fields(mock_flow, mock_logger, client):
    """Test that missing required fields in state results in an error redirect."""
    state_data = {} #Missing client_id and redirect_url
    serialized_state = json.dumps(state_data, separators=(',', ':'))

    with client.application.test_request_context():
        with client.session_transaction() as session:
            session['state'] = serialized_state
        response = client.get(url_for('gmail.oauth2callback'), query_string={'state': serialized_state, 'code': 'mock_code'})
        assert response.headers['Location'] == url_for('main.index')
    
    assert response.status_code == 302

    log_calls = [call[0][0] for call in mock_logger.exception.call_args_list]
    # Check that the log message contains 'Missing required fields', 'client_id', and 'redirect_url' regardless of order
    assert any(all(keyword in log_call for keyword in ['Missing required fields', 'client_id', 'redirect_url']) for log_call in log_calls)

@patch(GET_LOGS)
@patch(GET_FLOW, side_effect=Exception("Unexpected error"))
def test_oauth2callback_unexpected_exception(mock_flow, mock_logger, client):
    """Test that an unexpected exception is handled gracefully."""
    state_data = {'client_id': 'mock_client_id', 'redirect_url': 'http://testing.com'}
    serialized_state = json.dumps(state_data, separators=(',', ':'))

    with client.application.test_request_context():
        with client.session_transaction() as session:
            session['state'] = serialized_state
        response = client.get(url_for('gmail.oauth2callback'), query_string={'state': serialized_state, 'code': 'mock_code'})
        assert response.headers['Location'] == url_for('main.index')

    assert response.status_code == 302
    mock_logger.exception.assert_called_with("Unexpected error during OAuth callback: Unexpected error")

@patch(GET_LOGS)
@patch(GET_GMAIL_CREDENTIALS)
@patch(GET_FLOW)
@patch(GET_CLIENT)
def test_oauth2callback_database_error(mock_client, mock_flow, mock_gmail_credentials, mock_logger, client):
    """Test that a database error triggers rollback and results in an error redirect."""
    mock_flow_instance = MagicMock()
    mock_flow_instance.fetch_token.return_value = None

    mock_credentials = MagicMock(
        token='mock_access_token',
        refresh_token='mock_refresh_token'
    )
    mock_flow_instance.credentials = mock_credentials
    mock_flow.return_value = mock_flow_instance
   
    client_id = 'mock_client_id'
    redirect_url = 'http://testing.com'
    mock_client_instance = MagicMock(id=client_id)
    mock_client.query.get_or_404.return_value = mock_client_instance

    # Mock the GmailCredentials query to simulate no existing credentials
    mock_gmail_credentials.query.filter_by.return_value.first.return_value = None
    mock_gmail_credentials_instance = MagicMock()
    mock_gmail_credentials.return_value = mock_gmail_credentials_instance

    # Simulate a database error when saving credentials
    mock_gmail_credentials_instance.save.side_effect = SQLAlchemyError("Database error")

    state_data = {'client_id': client_id, 'redirect_url': redirect_url}
    serialized_state = json.dumps(state_data, separators=(',', ':'))
    
    with client.application.test_request_context():
        with client.session_transaction() as session:
            session['state'] = serialized_state
        response = client.get(url_for('gmail.oauth2callback'), query_string={'state': serialized_state, 'code': 'mock_code'})

    assert response.status_code == 302
    assert response.headers['Location'] == redirect_url
    mock_logger.exception.assert_called_with('Error storing credentials: Database error')

#========== Send Email Route ==========#
@patch(GET_GMAIL_SERVICE)
def test_send_email_route_success(mock_gmail_service, client):
    """Test the /send_email route for processing email sending requests."""
    # Mock the GmailService and its methods
    mock_gmail_service_instance = mock_gmail_service.return_value
    mock_gmail_service_instance.set_user_credentials.return_value = {}
    mock_gmail_service_instance.send_email.return_value = {}

    # Define the valid email data
    email_data = {
        'client_id': 'mock_client_id',
        'to_address': 'test@example.com',
        'subject': 'Test Subject',
        'body': 'This is a test email.'
    }

    with client.application.test_request_context():
        response = client.post(url_for('gmail.send_email'), json=email_data)

    assert response.status_code == 200
    assert response.get_json() == {'message': 'Email sent successfully'}

    mock_gmail_service_instance.set_user_credentials.assert_called_once_with(email_data['client_id'])
    mock_gmail_service_instance.send_email.assert_called_once_with(
        email_data['to_address'], email_data['subject'], email_data['body']
    )

@patch(GET_LOGS)
def test_send_email_route_missing_fields(mock_logger, client):
    """Test that the /send_email route returns an error when required fields are missing."""
    incomplete_email_data = {
        'client_id': 'mock_client_id',
        'body': 'This is a test email.'
    }

    with client.application.test_request_context():
        response = client.post(url_for('gmail.send_email'), json=incomplete_email_data)

    assert response.status_code == 400
    error_message = response.get_json().get('error', '')
    assert 'A required field is missing:' in error_message
    assert 'to_address' in error_message
    assert 'subject' in error_message

@patch(GET_LOGS)
def test_send_email_route_incorrect_data_types(mock_logger, client):
    """Test that the /send_email route returns an error when fields have incorrect data types."""
    incorrect_type_email_data = {
            'client_id': 'mock_client_id',
            'to_address': ['test@example.com'],  # Incorrect type
            'subject': 'Test Subject',
            'body': 12345  # Incorrect type
        }

    with client.application.test_request_context():
        response = client.post(url_for('gmail.send_email'), json=incorrect_type_email_data)

    assert response.status_code == 400
    error_message = response.get_json().get('error', '')

    assert 'Incorrect data type for fields:' in error_message
    assert 'to_address' in error_message
    assert 'body' in error_message

@patch(GET_GMAIL_SERVICE)
def test_send_email_route_invalid_client_id(mock_gmail_service, client):
    """Test that the /send_email route returns an error when an invalid client_id is provided."""
    mock_gmail_service_instance = mock_gmail_service.return_value
    #Mock the set_user_credentials method to return an error
    mock_gmail_service_instance.set_user_credentials.return_value = {'error': 'No credentials found for the user'}

    email_data = {
        'client_id': 'invalid_client_id',
        'to_address': 'test@example.com',
        'subject': 'Test Subject',
        'body': 'This is a test email.'
    }

    with client.application.test_request_context():
        response = client.post(url_for('gmail.send_email'), json=email_data)

    assert response.status_code == 400
    assert response.get_json() == {'error': 'No credentials found for the user'}
    mock_gmail_service_instance.set_user_credentials.assert_called_once_with(email_data['client_id'])

@patch(GET_GMAIL_SERVICE)
def test_send_email_route_email_service_error(mock_gmail_service, client):
    """Test that the /send_email route returns an error when the email service fails to send the email."""
    mock_gmail_service_instance = mock_gmail_service.return_value
    mock_gmail_service_instance.set_user_credentials.return_value = {'message': 'User credentials retrieved successfully'}
    #Mock the send_email method to return an error
    mock_gmail_service_instance.send_email.return_value = {'error': 'Failed to send email'}

    email_data = {
        'client_id': 'mock_client_id',
        'to_address': 'test@example.com',
        'subject': 'Test Subject',
        'body': 'This is a test email.'
    }

    with client.application.test_request_context():
        response = client.post(url_for('gmail.send_email'), json=email_data)

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Failed to send email'}

    mock_gmail_service_instance.set_user_credentials.assert_called_once_with(email_data['client_id'])
    mock_gmail_service_instance.send_email.assert_called_once_with(
        email_data['to_address'], email_data['subject'], email_data['body']
    )

@patch(GET_LOGS)
@patch(GET_GMAIL_SERVICE)
def test_send_email_route_unknown_exception(mock_gmail_service, mock_logger, client):
    """Test that the /send_email route handles unknown exceptions gracefully."""
    mock_gmail_service_instance = mock_gmail_service.return_value
    mock_gmail_service_instance.set_user_credentials.side_effect = Exception("Unexpected error")

    email_data = {
        'client_id': 'mock_client_id',
        'to_address': 'test@example.com',
        'subject': 'Test Subject',
        'body': 'This is a test email.'
    }

    with client.application.test_request_context():
        response = client.post(url_for('gmail.send_email'), json=email_data)

    assert response.status_code == 500
    assert response.get_json() == {'error': 'An unknown error occurred while sending the email'}

    mock_gmail_service_instance.set_user_credentials.assert_called_once_with(email_data['client_id'])

#========================================================================#
#=========================== Services Tests =============================#

#========================== Gmail Service ===============================#

#========== Send Email ==========#
def test_gmail_service_send_email_success(client):
    """Test the GmailService send_email method for successful email sending."""
    pass

def test_gmail_service_send_email_error(client):
    """Test the GmailService send_email method for error handling."""
    pass

#========== Refresh Access Token ==========#
def test_gmail_service_refresh_access_token_success(client):
    """Test the GmailService refresh_access_token method for successful token refresh."""
    pass

def test_gmail_service_refresh_access_token_error(client):
    """Test the GmailService refresh_access_token method for error handling."""
    pass

#========== Structure Email Data ==========#
def test_gmail_service_structure_email_data_success(client):
    """Test the GmailService structure_email_data method for successful email data structure."""
    pass

def test_gmail_service_structure_email_data_error(client):
    """Test the GmailService structure_email_data method for error handling."""
    pass

#========== Set User Credentials ==========#
def test_gmail_service_set_user_credentials_success(client):
    """Test the GmailService set_user_credentials method for successful user credentials retrieval."""
    pass

def test_gmail_service_set_user_credentials_error(client):
    """Test the GmailService set_user_credentials method for error handling."""
    pass










