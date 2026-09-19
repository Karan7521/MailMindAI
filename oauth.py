from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose"
]

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        Path(__file__).with_name("credentials.json"), SCOPES
    )
    creds = flow.run_local_server(port=8081)
    print("\n==============================")
    print("REFRESH TOKEN")
    print("==============================")
    print(creds.refresh_token)
    print("==============================")


if __name__ == "__main__":
    main()