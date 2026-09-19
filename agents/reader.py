from tools.gmail_tool import get_unread_emails

def read_emails(gmail_service=None):
    return get_unread_emails(gmail_service)