import multiprocessing
import threading
import click
from openai import OpenAI
import os
import math
from flask import Blueprint, request, jsonify
from standard_pipelines.bots.telegram_bot import TelegramBot
from standard_pipelines.bots.skype_bot import SkypeBot
import standard_pipelines.assistants.redtrack.config.config as config
import time
from openai.types.beta import Assistant

redtrack_bp = Blueprint('redtrack', __name__, url_prefix='/redtrack')

telegram_bot : TelegramBot = None
skype_bot : SkypeBot = None
def start_bots():
    print("starting RedTrack bots")
    # def start_telegram_bot():
    global telegram_bot
    telegram_bot = TelegramBot(config.TELEGRAM_TOKEN, greeting_handler, convo_start_handler, message_handler)

    # def start_skype_bot():
    #     global skype_bot
    #     skype_bot = SkypeBot(config.SKYPE_USERNAME, config.SKYPE_PASSWORD, greeting_handler, convo_start_handler, message_handler)

    # polling_thread = threading.Thread(target=start_telegram_bot)
    # polling_thread.start()
    # telegram_process = multiprocessing.Process(target=start_telegram_bot)
    # skype_process = multiprocessing.Process(target=start_skype_bot)

    # telegram_process.start()
    # skype_process.start()

    # start_telegram_bot()

    print("RedTrack bots started")

@redtrack_bp.route('/start', methods=['POST'])
def redtrack_start():
    data = request.get_json()
    
    # Define required fields
    required_fields = ['first_name', 'last_name', 'platform', 'username']
    
    # Check for missing fields
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({
            'error': 'Missing required fields',
            'missing_fields': missing
        }), 400

    first_name = data['first_name']
    last_name = data['last_name']
    platform = data['platform']
    username = data['username']

    # (Optional) Validate platform if necessary
    # allowed_platforms = ['skype', 'whatsapp', 'telegram']
    # if platform.lower() not in allowed_platforms:
    #     return jsonify({
    #         'error': 'Invalid platform',
    #         'allowed_platforms': allowed_platforms
    #     }), 400


    if platform == "skype":
        skype_bot.start_chat(username)


    # Process the data as needed
    # For now, we'll just return the received data as confirmation.
    return 200


thread_map : dict[str, str] = {}
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

def greeting_handler(username: str):
    print("greeting_handler",config.GREETING)
    return config.GREETING.format(username=username, link=config.LINK)

def convo_start_handler(convo_id: str, message_text: str) -> None:
    print("convo_start_handler", message_text)

    thread = openai_client.beta.threads.create_and_run_poll(assistant_id=config.ASSISTANT["id"])
    thread_id = thread.thread_id;
    thread_map[convo_id] = thread_id

    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="assistant",
        content=message_text
    )

    print("created thread:", thread_id)

def message_handler(convo_id: str, username: str, message_text: str) -> str:
    print("message_handler", username, message_text)

    
    thread_id = thread_map[convo_id]

    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_text
    )

    run = openai_client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=config.ASSISTANT["id"]
    )
 
    if run.status == 'completed':
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread_id
        )
        print(messages)
    else:
        print(run.status)

    if run.required_action:
        # Define the list to store tool outputs
        tool_outputs = []
 
        # Loop through each tool in the required action section
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            print(tool)

            if tool.function.name == "schedule_call":
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": "true"
                })
                # cancel the run because we don't want the bot to speak naturally
                openai_client.beta.threads.runs.cancel(run.id, thread_id=thread_id)
                return config.SCHEDULE_CALL_MESSAGE.format(link=config.LINK)
        
        # Submit all tool outputs at once after collecting them in a list
        if tool_outputs:
            try:
                run = openai_client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                print("Tool outputs submitted successfully.")
            except Exception as e:
                print("Failed to submit tool outputs:", e)
        else:
            print("No tool outputs to submit.")

    messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
    print(messages)

    return messages.data[0].content[0].text.value

@click.command('redtrack')
@click.argument('operation', type=click.Choice(['push']))
@click.argument('parameter', type=click.Choice(['bot', 'data']))
def handle_command(operation, parameter):
    print(operation, '|', parameter)

    if operation == 'push':
        if parameter == 'bot':
            push_bot()
        elif parameter == 'data':
            push_data()

def push_bot():
    print("pushing bot...")

    assistant : Assistant = None
    if config.ASSISTANT["id"] is None:
        assistant = openai_client.beta.assistants.create(
            name=config.ASSISTANT["name"],
            model=config.ASSISTANT["model"],
            instructions=config.ASSISTANT["system_prompt"],
            tools=config.ASSISTANT["tools"],
            tool_resources=config.ASSISTANT["tool_resources"]
        )
        config.ASSISTANT["id"] = assistant.id
        print("created assistant", assistant.id)
    else:
        assistant = openai_client.beta.assistants.retrieve(config.ASSISTANT["id"])
        print("retrieved assistant", assistant.id)

        openai_client.beta.assistants.update(
            assistant_id=config.ASSISTANT["id"],
            name=config.ASSISTANT["name"],
            model=config.ASSISTANT["model"],
            instructions=config.ASSISTANT["system_prompt"],
            tools=config.ASSISTANT["tools"],
            tool_resources=config.ASSISTANT["tool_resources"]
        )
        print("updated assistant", assistant.id)

    assistant_id = assistant.id
    print("assistant_id:", assistant_id)
    print("bot push complete")

def push_data():
    print("pushing data...")

    if config.VECTOR_STORE["id"] is None:
        vector_store = openai_client.beta.vector_stores.create(
            name=config.VECTOR_STORE["name"]
        )
        config.VECTOR_STORE["id"] = vector_store.id
        print("created vector store", vector_store.id)
    else:
        vector_store = openai_client.beta.vector_stores.retrieve(config.VECTOR_STORE["id"])
        print("retrieved vector store", vector_store.id)

        openai_client.beta.vector_stores.update(
            vector_store_id=config.VECTOR_STORE["id"],
            name=config.VECTOR_STORE["name"]
        )
        print("updated vector store", vector_store.id)

    MAX_BATCH_SIZE = 500

    if not vector_store:
        print("No vector store configured. Skipping file upload.")
    else:
        data_folder = os.path.join(os.getcwd(), "standard_pipelines/assistants/redtrack/data/processed")
        if not os.path.isdir(data_folder):
            print(f"Data folder '{data_folder}' does not exist.")
        else:
            print("Syncing vector store with folder:", data_folder)
            
            # Collect all file paths in the folder (and subfolders, if any)
            file_paths = []
            for root, _, files in os.walk(data_folder):
                for file_name in files:
                    file_paths.append(os.path.join(root, file_name))
            
            # If there are no files, just exit
            if not file_paths:
                print("No files found in data folder to upload.")
            else:
                # Calculate how many batches we need
                total_files = len(file_paths)
                num_batches = math.ceil(total_files / MAX_BATCH_SIZE)
                print(f"Total files: {total_files}. Uploading in {num_batches} batches of up to {MAX_BATCH_SIZE} files each.")
                
                start_index = 0
                for batch_index in range(num_batches):
                    # Slice the current batch of file paths
                    batch_file_paths = file_paths[start_index : start_index + MAX_BATCH_SIZE]
                    start_index += MAX_BATCH_SIZE
                    
                    # Open each file in this batch
                    file_streams = []
                    try:
                        for file_path in batch_file_paths:
                            f = open(file_path, "rb")
                            file_streams.append(f)
                        
                        print(f"Uploading batch {batch_index + 1}/{num_batches} with {len(file_streams)} files.")
                        
                        # Upload the batch
                        file_batch = openai_client.beta.vector_stores.file_batches.upload_and_poll(
                            vector_store_id=vector_store.id,
                            files=file_streams
                        )
                        
                        print("File batch status:", file_batch.status)
                        print("File batch file counts:", file_batch.file_counts)
                    
                    finally:
                        # Close file streams for this batch
                        for f in file_streams:
                            f.close()

        print("File batch upload complete.")