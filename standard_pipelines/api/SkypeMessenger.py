from skpy import Skype

class SkypeMessenger:
    def __init__(self, username: str, password: str):
        """
        Initialize the Skype client with your Skype username and password.
        """
        self.skype = Skype(username, password)
        
    def send_message(self, conversation_id: str, message: str):
        """
        Send a message to a given conversation (channel or one-on-one chat).
        
        :param conversation_id: The ID for the Skype conversation. 
                               For one-on-one, this is usually "live:<skype_username>".
                               For group chats, it is often a longer string like 
                               "19:<some_unique_id>@thread.skype".
        :param message: The text content of the message you want to send.
        """
        try:
            chat = self.skype.chats.chat(conversation_id)
            chat.sendMsg(message)
            print(f"Message sent to {conversation_id} successfully.")
        except Exception as e:
            print(f"Failed to send message: {e}")

if __name__ == "__main__":
    email = "devbot-2077@hotmail.com"
    password = "ZdQgj41k3cZHZv"
    conversation_id = "19:f51264e637b5453684a818b51cf4e276@thread.v2"
    skype = SkypeMessenger(email, password)
        
    skype.send_message(conversation_id, "Hello, this is a test message from the Skype API!")