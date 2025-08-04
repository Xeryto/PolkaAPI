import os
import httpx

class MailService:
    def __init__(self, api_key, sender_email, sender_name, list_id):
        self.api_key = api_key
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.list_id = list_id
        self.base_url = "https://api.unisender.com/ru/api/sendEmail"

    def send_email(self, to_email, subject, html_content):
        print(f"--- SIMULATED EMAIL ---")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Content:\n{html_content}")
        print(f"-----------------------")
        # Temporarily disable actual sending
        # params = {
        #     "format": "json",
        #     "api_key": self.api_key,
        #     "email": to_email,
        #     "sender_name": self.sender_name,
        #     "sender_email": self.sender_email,
        #     "subject": subject,
        #     "body": html_content,
        #     "list_id": self.list_id,
        # }
        # try:
        #     response = httpx.post(self.base_url, params=params)
        #     response.raise_for_status()
        #     return response.json()
        # except httpx.HTTPStatusError as e:
        #     print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        #     return None
        # except httpx.RequestError as e:
        #     print(f"An error occurred while requesting {e.request.url!r}: {e}")
        #     return None
        # except Exception as e:
        #     print(f"An unexpected error occurred: {e}")
        #     return None
        return {"status": "simulated_success"} # Return a success-like response

mail_service = MailService(
    os.getenv("UNISENDER_API_KEY"),
    os.getenv("UNISENDER_FROM_EMAIL"),
    os.getenv("UNISENDER_FROM_NAME"),
    os.getenv("UNISENDER_LIST_ID")
)