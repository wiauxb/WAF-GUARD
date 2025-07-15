import streamlit as st
import requests
from langchain_core.messages import AIMessage, HumanMessage, message_to_dict, messages_from_dict, ToolMessage
import time

# URLs
WS_URL = "ws://chatbot:8005/ws"
CHAT_URL = "http://chatbot:8005/chat"
BASIC_GRAPH = CHAT_URL + "/basic_graph"
UI_GRAPH = CHAT_URL + "/ui_graph"
REASONING_GRAPH = CHAT_URL + "/reasoning_graph"

# =====================
# Authentication Utils
# =====================
def login_user(username, password):
    """Authenticate user and return token if successful."""
    try:
        response = requests.post(f"{CHAT_URL}/login", data={"username": username, "password": password}, headers={"Content-Type": "application/x-www-form-urlencoded"})
        print(response.text, flush=True)
        if response.status_code == 200:
            return response.json()
        return response
    except Exception as e:
        st.error(f"Login error: {e}")
    return None

def register_user(username, password):
    """Register a new user and return token if successful."""
    try:
        response = requests.post(f"{CHAT_URL}/register", data={"username": username, "password": password}, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Registration error: {e}")
    return None

# =====================
# Thread (Conversation) Management
# =====================
def get_threads():
    """Fetch all threads for the authenticated user."""
    try:
        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{CHAT_URL}/threads", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching threads: {e}")
        return []

def get_thread_messages(thread_id):
    """Fetch all messages for a given thread."""
    try:
        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{CHAT_URL}/threads/{thread_id}", headers=headers)
        if response.status_code == 200:
            messages = response.json()
            print(f"Messages from API: {messages}", flush=True)
            return messages_from_dict(messages)
        return []
    except Exception as e:
        st.error(f"Error fetching thread messages: {e}")
        return []

def create_new_thread():
    """Create a new thread and update session state."""
    try:
        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{CHAT_URL}/threads", headers=headers)
        if response.status_code == 200:
            thread_id = response.json()
            st.session_state["selected_thread"] = thread_id
            st.session_state["messages"] = []
            st.toast("New thread created", icon="🆕")
            st.rerun()
        else:
            st.error("Error creating thread.")
    except Exception as e:
        st.error(f"Error creating thread: {e}")
        print(f"Error creating thread: {e}", flush=True)

def delete_thread(thread_id):
    """Delete a thread by its ID and update session state accordingly."""
    try:
        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(f"{CHAT_URL}/threads/{thread_id}", headers=headers)
        if response.status_code == 200:
            st.toast("Thread deleted successfully", icon="🗑️")
            # Remove thread from state and update selected_thread/messages
            threads = get_threads()
            if threads:
                st.session_state["selected_thread"] = threads[0]["id"]
                st.session_state["messages"] = get_thread_messages(threads[0]["id"])
            else:
                st.session_state["selected_thread"] = None
                st.session_state["messages"] = []
            st.rerun()
        else:
            st.error("Error deleting thread.")
    except Exception as e:
        st.error(f"Error deleting thread: {e}")
        print(f"Error deleting thread: {e}", flush=True)

def rename_thread(thread_id, new_title):
    """Rename a thread by its ID."""
    try:
        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.put(f"{CHAT_URL}/threads/{thread_id}", json={"new_title": new_title}, headers=headers)
        if response.status_code == 200:
            st.toast("Thread renamed successfully", icon="✏️")
            st.rerun()
        else:
            st.error("Error renaming thread.")
    except Exception as e:
        st.error(f"Error renaming thread: {e}")
        print(f"Error renaming thread: {e}", flush=True)

def send_message(message):
    """Send a message to a specific thread."""
    try:
        graph=st.session_state.get("selected_graph")
        print(f"Graph selected: {graph}", flush=True)
        token = st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"messages": [message_to_dict(message)], "config": {"thread_id": st.session_state.get("selected_thread"), "user_id": st.session_state.get("user_id")}}
        if graph == "UI tools":
            response = requests.post(UI_GRAPH, json=payload, headers=headers)
        elif graph == "Reasoning":
            response = requests.post(REASONING_GRAPH, json=payload, headers=headers)
        elif graph == "Basic":
            response = requests.post(BASIC_GRAPH, json=payload, headers=headers)
        if response.status_code == 200:
            response_messages = messages_from_dict(response.json())
            return response_messages
        else:
            st.error("Error sending message.")
            return []
    except Exception as e:
        st.error(f"Error sending message: {e}")
        print(f"Error sending message: {e}", flush=True)
        return []

# =====================
# Dialogs
# =====================
@st.dialog("🔐 Login required")
def login_dialog():
    with st.form("login_form"):
        st.markdown("## Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        login_submitted = col1.form_submit_button("Login")
        register_clicked = col2.form_submit_button("Create account")

        if login_submitted:
            user_data = login_user(username, password)
            if user_data:
                st.session_state["authenticated"] = True
                st.session_state["token"] = user_data["access_token"]
                st.session_state["username"] = username
                st.session_state["user_id"] = user_data["user_id"]
                st.rerun()
            else:
                st.error("Invalid username or password.")

        if register_clicked:
            st.session_state["show_register"] = True
            st.rerun()

@st.dialog("📝 Create account")
def register_dialog():
    with st.form("register_form"):
        st.markdown("## Create account")
        username = st.text_input("Username (new)")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        col1, col2 = st.columns(2)
        submit = col1.form_submit_button("Register")
        cancel = col2.form_submit_button("Back")

        if submit:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                user_data = register_user(username, password)
                if user_data:
                    st.success("Account created successfully ✅")
                    st.session_state["authenticated"] = True
                    st.session_state["token"] = user_data["access_token"]
                    st.session_state["username"] = username
                    st.session_state["show_register"] = False
                    st.rerun()

        if cancel:
            st.session_state["show_register"] = False
            st.rerun()

@st.dialog("Edit thread")
def edit_thread_dialog(thread_id, title):
    new_title = st.text_input("New title", value=title, key=f"edit_title_{thread_id}")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Rename", key=f"validate_{thread_id}"):
            if new_title:
                rename_thread(thread_id, new_title)
            else:
                st.error("Title cannot be empty.")
            st.rerun()
    with col2:
        if st.button("Delete", key=f"delete_{thread_id}"):
            delete_thread(thread_id)
            st.rerun()
    with col3:
        if st.button("Cancel", key=f"cancel_{thread_id}"):
            st.rerun()


def extract_tool_messages(messages):
    """Extract tool messages from the list of messages."""
    #Iterate through messages and collect tools messages and the previous ai message that contains the parameters of the tool call
    # The function should return a list of dict with keys name, args and response 
    tool_messages = []
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            print(f"I value at tool message: {i}", flush=True)
            print(f"Type of i: {type(i)}", flush=True)
            tool_call = {
                "name": msg.name,
                "response": msg.content
            }
            # Check if the previous message is an AIMessage
            if i > 0 and isinstance(messages[i - 1], AIMessage):
                previous_message = messages[i - 1]
                tool_call["args"] = previous_message.tool_calls[0]["args"]
            tool_messages.append(tool_call)
    return tool_messages

# =====================
# Main App
# =====================
st.set_page_config(page_title="WAF Chatbot", layout="wide")

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "show_register" not in st.session_state:
    st.session_state["show_register"] = False

# Show dialogs if not authenticated
if not st.session_state["authenticated"]:
    if st.session_state["show_register"]:
        register_dialog()
    else:
        login_dialog()
    st.stop()

# Sidebar options
st.sidebar.title("Options")
st.session_state["selected_graph"] = st.sidebar.selectbox("Choose a graph", ["UI tools", "Reasoning", "Basic"])

if st.sidebar.button("New Thread", key="new_thread"):
    create_new_thread()

# List threads
st.sidebar.markdown("### Threads")
threads = get_threads()
if not threads:
    print("No threads found, creating a new thread", flush=True)
    # create_new_thread()

# Selected thread state
if "selected_thread" not in st.session_state and threads:
    st.session_state.selected_thread = threads[0]["id"]

for thread in threads:
    col1, col2 = st.sidebar.columns([0.8, 0.2])
    button_type = "primary" if thread["id"] == st.session_state.get("selected_thread") else "secondary"
    if col1.button(thread["title"], key=thread["id"], use_container_width=True, type=button_type):
        st.session_state.selected_thread = thread["id"]
        st.session_state.messages = get_thread_messages(thread["id"])
        st.rerun()
    with col2:
        if st.button("⋮", key=f"menu_{thread['id']}"):
            edit_thread_dialog(thread["id"], thread["title"])

# Main display
st.title("WAF-ssistant")

# Initialize messages
if "messages" not in st.session_state and "selected_thread" in st.session_state:
    st.session_state.messages = get_thread_messages(st.session_state.selected_thread)

# Display messages
for msg in st.session_state.get("messages", []):
    if isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(msg.content)
    elif isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)

# Handle new user input
if prompt := st.chat_input("Ask your question here..."):
    st.chat_message("user").markdown(prompt)
    msg = HumanMessage(content=prompt)
    st.session_state.messages.append(msg)
    with st.spinner("Analyzing..."):
        response_msg = send_message(msg)
        print(f"Response messages: {response_msg}", flush=True)
        last_message = response_msg[-1]
        #remove the last message from response_msg
        response_msg = response_msg[:-1]
        tool_messages= extract_tool_messages(response_msg)

        with st.chat_message("assistant"):
            st.markdown(last_message.content)
            review = st.feedback("thumbs")
            with st.expander("Tools details"):
                for tool_message in tool_messages:
                    with st.expander(f"{tool_message['name']}"):
                        st.markdown(f"Args: {tool_message['args']}")
                        st.markdown(f"Response: {tool_message['response']}")
        st.session_state.messages.append(last_message)



