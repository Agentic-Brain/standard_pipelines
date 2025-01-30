from twilio.rest import Client

class TwilioMessenger:
    """
    A simple wrapper around the Twilio Python client to send SMS and WhatsApp messages.
    """

    def __init__(self, account_sid: str, auth_token: str, twilio_phone_number: str):
        """
        :param account_sid: Your Twilio Account SID
        :param auth_token: Your Twilio Auth Token
        :param twilio_phone_number: The Twilio phone number (in E.164 format) you want to send messages from.
                                   Example: '+12345678900'
        """
        self.client = Client(account_sid, auth_token)
        self.twilio_phone_number = twilio_phone_number

    def send_sms(self, to_phone_number: str, message: str):
        """
        Send an SMS message using Twilio.
        
        :param to_phone_number: Recipient’s phone number in E.164 format. Example: '+15555555555'
        :param message: Text of the SMS message to send
        :return: A Message instance with information about the sent message
        """
        response = self.client.messages.create(
            body=message,
            from_=self.twilio_phone_number,  # Twilio phone number must be SMS-capable
            to=to_phone_number
        )
        return response

    def send_whatsapp(self, to_phone_number: str, message: str):
        """
        Send a WhatsApp message using Twilio.
        
        :param to_phone_number: Recipient’s phone number in E.164 format. Example: '+15555555555'
        :param message: Text of the WhatsApp message to send
        :return: A Message instance with information about the sent message
        """
        response = self.client.messages.create(
            body=message,
            from_='whatsapp:' + self.twilio_phone_number,  # Twilio WhatsApp sender
            to='whatsapp:' + to_phone_number
        )
        return response

if __name__ == "__main__":
    # Replace these placeholder values with your actual Twilio credentials
    ACCOUNT_SID = "AC3c5a5c29f4eebcacff000cafd03c8b50"
    AUTH_TOKEN = "6fd5ccc03068e3fbe2b2aa30ee54dbc0"
    # AUTH_SID = "SKe363ce37bf641be262818a8dfa3d4633"
    # AUTH_SECRET = "PdMXWElbHSLOyMqyymr5F3UmWJT4P63S"
    TWILIO_PHONE_NUMBER = "+14155238886"  # Your Twilio phone number in E.164 format

    recipient_phone_number = "+15175151699"
    
    messenger = TwilioMessenger(ACCOUNT_SID, AUTH_TOKEN, TWILIO_PHONE_NUMBER)

    # # Send SMS
    # sms_response = messenger.send_sms(recipient_phone_number, "Hello from Twilio SMS!")
    # print("SMS sent! SID:", sms_response.sid)

    # Send WhatsApp
    whatsapp_response = messenger.send_whatsapp(recipient_phone_number, "Hello from Twilio WhatsApp!")
    print("WhatsApp message sent! SID:", whatsapp_response.sid)
