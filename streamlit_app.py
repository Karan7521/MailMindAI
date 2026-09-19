import streamlit as st

from tools.gmail_tool import (
    get_gmail_service,
    get_unread_emails,
    create_draft,
)


st.set_page_config(
    page_title="AI Email Inbox Triage",
    page_icon="📧",
    layout="wide",
)


st.title("📧 AI Email Inbox Triage")
st.write(
    "Automatically fetch and organize your unread Gmail emails."
)


# --------------------------------------------------
# Connect to Gmail
# --------------------------------------------------

if st.button("🔗 Connect to Gmail"):

    try:
        service = get_gmail_service()

        st.session_state["gmail_service"] = service

        st.success("✅ Gmail connected successfully!")

    except Exception as e:

        st.error(
            f"❌ Gmail connection failed:\n\n{e}"
        )


# --------------------------------------------------
# Fetch Emails
# --------------------------------------------------

if st.button("📥 Fetch Unread Emails"):

    try:

        service = st.session_state.get(
            "gmail_service"
        )

        if service is None:
            service = get_gmail_service()
            st.session_state["gmail_service"] = service

        emails = get_unread_emails(service)

        st.session_state["emails"] = emails

        if not emails:

            st.info("📭 No unread emails found.")

        else:

            st.success(
                f"Found {len(emails)} unread email(s)."
            )

    except Exception as e:

        st.error(
            f"❌ Failed to fetch emails:\n\n{e}"
        )


# --------------------------------------------------
# Display Emails
# --------------------------------------------------

emails = st.session_state.get(
    "emails",
    []
)


if emails:

    st.subheader("📨 Unread Emails")

    for index, email in enumerate(emails):

        with st.container():

            st.markdown(
                f"### {index + 1}. "
                f"{email['subject'] or '(No Subject)'}"
            )

            st.write(
                f"**From:** {email['sender']}"
            )

            st.write(
                f"**Preview:** {email['snippet']}"
            )

            st.divider()


# --------------------------------------------------
# Draft Reply
# --------------------------------------------------

st.subheader("✍️ Create Draft Reply")

to_email = st.text_input(
    "Recipient Email"
)

subject = st.text_input(
    "Subject"
)

body = st.text_area(
    "Reply"
)


if st.button("📝 Create Gmail Draft"):

    if not to_email or not subject or not body:

        st.warning(
            "Please fill all fields."
        )

    else:

        try:

            service = st.session_state.get(
                "gmail_service"
            )

            if service is None:
                service = get_gmail_service()
                st.session_state["gmail_service"] = service

            draft = create_draft(
                service=service,
                to=to_email,
                subject=subject,
                body=body,
            )

            st.success(
                "✅ Draft created successfully!"
            )

            st.write(
                "Draft ID:",
                draft.get("id")
            )

        except Exception as e:

            st.error(
                f"❌ Failed to create draft:\n\n{e}"
            )