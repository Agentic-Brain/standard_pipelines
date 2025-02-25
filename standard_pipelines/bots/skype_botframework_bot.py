# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class Conversation:
    def __init__(self, openai_thread_id: str, chat_service: str):
        self.openai_thread_id = openai_thread_id
        self.chat_service = chat_service

# Store conversations in memory
convo_map: dict[str, Conversation] = {}

def create_new_conversation(conversation_id: str, openai_thread_id: str, chat_service: str):
    """Create and store a new conversation"""
    global convo_map
    convo_map[conversation_id] = Conversation(
        openai_thread_id=openai_thread_id,
        chat_service=chat_service
    )
    app.logger.info(f"Created new conversation with OpenAI thread: {openai_thread_id}")

def get_conversation(conversation_id: str, chat_service: str) -> Optional[Conversation]:
    """Retrieve an existing conversation"""
    global convo_map
    return convo_map.get(conversation_id)

def get_access_token():
    """
    Obtain an OAuth access token from Microsoft's identity endpoint.
    This token is used to authenticate outgoing messages via the Bot Framework.
    """
    url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': APP_ID,
        'client_secret': APP_SECRET,
        'scope': 'https://api.botframework.com/.default'
    }
    response = requests.post(url, data=data, headers=headers)
    token = response.json().get('access_token')
    return token

def send_reply(service_url, conversation_id, message, reply_to_id=None):
    """
    Send a reply message back to the conversation using the Bot Framework REST API.
    """
    token = get_access_token()
    url = f"{service_url}/v3/conversations/{conversation_id}/activities"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}"
    }
    payload = {
        "type": "message",
        "text": message
    }
    if reply_to_id:
        payload["replyToId"] = reply_to_id
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def handle_message(conversation_id: str, message_text: str, service: str = "botframework") -> str:
    """Handle incoming messages and return the assistant's response"""
    app.logger.info(f"Handling message for conversation: {conversation_id}")
    
    convo = get_conversation(conversation_id, service)
    if not convo:
        # Create new conversation with OpenAI
        start_time = time.time()
        app.logger.info("Creating new OpenAI thread...")
        
        thread = openai_client.beta.threads.create_and_run_poll(
            assistant_id=ASSISTANT_ID
        )
        create_new_conversation(conversation_id, thread.thread_id, service)
        convo = get_conversation(conversation_id, service)
        
        elapsed = time.time() - start_time
        app.logger.info(f"Created new OpenAI thread {thread.thread_id} in {elapsed:.2f}s")

    # Add user message to thread
    start_time = time.time()
    app.logger.info("Adding message to thread...")
    
    message = openai_client.beta.threads.messages.create(
        thread_id=convo.openai_thread_id,
        role="user",
        content=message_text
    )
    
    elapsed = time.time() - start_time
    app.logger.info(f"Added message to thread in {elapsed:.2f}s")

    # Run the assistant
    start_time = time.time()
    app.logger.info("Running assistant...")
    
    run = openai_client.beta.threads.runs.create_and_poll(
        thread_id=convo.openai_thread_id,
        assistant_id=ASSISTANT_ID
    )
    
    elapsed = time.time() - start_time
    app.logger.info(f"Assistant run completed in {elapsed:.2f}s with status: {run.status}")

    if run.status != 'completed':
        app.logger.error(f"Run failed with status: {run.status}")
        return "I apologize, but I encountered an error processing your message."

    # Get the latest message
    start_time = time.time()
    app.logger.info("Fetching assistant response...")
    
    messages = openai_client.beta.threads.messages.list(
        thread_id=convo.openai_thread_id
    )
    
    elapsed = time.time() - start_time
    app.logger.info(f"Fetched assistant response in {elapsed:.2f}s")
    
    if not messages.data:
        app.logger.error("No messages returned from assistant")
        return "I apologize, but I couldn't generate a response."

    response = messages.data[0].content[0].text.value
    app.logger.info(f"Assistant response: {response[:100]}...")  # Log first 100 chars of response
    return response

@app.route('/api/messages', methods=['POST'])
def messages():
    """
    This endpoint is called by the Bot Framework when a message arrives.
    It extracts conversation details, sends the incoming message to your custom assistant,
    and returns the assistant's reply back to the conversation.
    """
    data = request.get_json()
    conversation_id = data['conversation']['id']
    service_url = data['serviceUrl']
    reply_to_id = data.get('id')
    incoming_text = data.get('text', '')
    
    # Get reply from assistant
    reply_text = handle_message(conversation_id, incoming_text)
    
    # Send reply via Bot Framework
    send_reply(service_url, conversation_id, reply_text, reply_to_id)
    
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    # For local testing, you can use ngrok to expose your local server publicly.
    app.run(port=5020, debug=True)