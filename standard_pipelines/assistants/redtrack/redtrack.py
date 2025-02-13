from openai import OpenAI
import os
import math

api_key = "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"

vector_store_config = {
    "id" : "vs_67ad4870761881918ee49d874b3c03e0",
    "name" : "RedTrack Knowledge Base"
}

assistant_config = {
    "id" : "asst_TT69GyMnGA8Oy9YfnuXfiUW7",
    "name" : "Redtrack Inbound Lead Outreach Tool",
    "model" : "gpt-4o-mini",
    "system_prompt" : "You are the RedTrack booking agent bot. Answer any questions the client may have and when they are ready, use the schedule_call function to schedule a call with a human.",
    "tools" : [
        {
            "type": "function",
            "function": {
                "name": "schedule_call",
                "strict": True,
                "description": "Send a link to the client that will allow them to schedule a call with a human.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                    "required": []
                }
            }
        },
        {
            "type": "file_search"
        }
    ],
    "tool_resources" : {
        "file_search" : {
            "vector_store_ids" : [] if vector_store_config["id"] is None else [vector_store_config["id"]]
        }
    },


}

client = OpenAI(api_key=api_key)

if vector_store_config["id"] is None:
    vector_store = client.beta.vector_stores.create(
        name=vector_store_config["name"]
    )
    vector_store_config["id"] = vector_store.id
    print("created vector store", vector_store.id)
else:
    vector_store = client.beta.vector_stores.retrieve(vector_store_config["id"])
    print("retrieved vector store", vector_store.id)

    client.beta.vector_stores.update(
        vector_store_id=vector_store_config["id"],
        name=vector_store_config["name"]
    )
    print("updated vector store", vector_store.id)


assistant = None
if assistant_config["id"] is None:
    assistant = client.beta.assistants.create(
        name=assistant_config["name"],
        model=assistant_config["model"],
        instructions=assistant_config["system_prompt"],
        tools=assistant_config["tools"],
        tool_resources=assistant_config["tool_resources"]
    )
    assistant_config["id"] = assistant.id
    print("created assistant", assistant.id)
else:
    assistant = client.beta.assistants.retrieve(assistant_config["id"])
    print("retrieved assistant", assistant.id)

    client.beta.assistants.update(
        assistant_id=assistant_config["id"],
        name=assistant_config["name"],
        model=assistant_config["model"],
        instructions=assistant_config["system_prompt"],
        tools=assistant_config["tools"],
        tool_resources=assistant_config["tool_resources"]
    )
    print("updated assistant", assistant.id)

assistant_id = assistant.id
print("assistant_id", assistant_id)

print(assistant.tool_resources.file_search.to_json())

# Assuming the "os" module is already imported elsewhere in the project

# Attempt to retrieve the vector store from the assistant's tool resources

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
                    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
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


print("assistant push complete")