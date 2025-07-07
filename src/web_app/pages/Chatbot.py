import streamlit as st
import requests
from langchain_core.messages import AIMessage, HumanMessage, message_to_dict, messages_from_dict
import time

# URLs
WS_URL = "ws://chatbot:8005/ws"
CHAT_URL = "http://chatbot:8005/chat"
BASIC_GRAPH = CHAT_URL + "/basic_graph"
UI_GRAPH = CHAT_URL + "/ui_graph"
REASONING_GRAPH = CHAT_URL + "/reasoning_graph"


def login_user(username, password):
    try:
        response = requests.post(f"{CHAT_URL}/login", data={"username": username, "password": password},headers={"Content-Type": "application/x-www-form-urlencoded"})
        print(response.text, flush=True)
        # response={"access_token": "mock_token", "username": "mock_user", "status_code": 200}
        if response.status_code == 200:
            return response.json()
        return response
    except Exception as e:
        st.error(f"Erreur lors de la connexion : {e}")
    return None

def register_user(username, password):
    try:
        response = requests.post(f"{CHAT_URL}/register", data={"username": username, "password": password},headers={"Content-Type": "application/x-www-form-urlencoded"})
        # response = {"access_token": "mock_token", "username": "mock_user", "status_code": 200}
        if response.status_code == 200:
            return response.json()
        # return response
    except Exception as e:
        st.error(f"Erreur d'inscription : {e}")
    return None


def get_threads():
    try:
        token= st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{CHAT_URL}/threads", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Erreur lors de la récupération des threads : {e}")
        return []

def get_thread_message(thread_id):
    try:
        token= st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{CHAT_URL}/threads/{thread_id}", headers=headers)
        if response.status_code == 200:
            messages = response.json()
            print(f"Messages from api: {messages}", flush=True)
            return messages_from_dict(messages)
        return []
    except Exception as e:
        st.error(f"Erreur lors de la récupération des messages du thread : {e}")
        return []
    
def new_thread():
    try:
        token= st.session_state.get("token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{CHAT_URL}/threads", headers=headers)
        if response.status_code == 200:
            thread_id = response.json()
            st.session_state["selected_conversation"] = thread_id
            st.toast("Nouveau thread créé", icon="🆕")
            st.rerun()
        else:
            st.error("Erreur lors de la création du thread.")
    except Exception as e:
        st.error(f"Erreur lors de la création du thread : {e}")
        print(f"Erreur lors de la création du thread : {e}", flush=True)
    



@st.dialog("🔐 Connexion requise")
def login_dialog():
    with st.form("login_form"):
        st.markdown("## Connexion")
        username = st.text_input("username")
        password = st.text_input("Mot de passe", type="password")
        col1, col2 = st.columns(2)
        login_submitted = col1.form_submit_button("Se connecter")
        register_clicked = col2.form_submit_button("Créer un compte")

        if login_submitted:
            user_data = login_user(username, password)
            if user_data:
                st.session_state["authenticated"] = True
                st.session_state["token"] = user_data["access_token"]
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("username ou mot de passe invalide.")

        if register_clicked:
            st.session_state["show_register"] = True
            st.rerun()


@st.dialog("📝 Création de compte")
def register_dialog():
    with st.form("register_form"):
        st.markdown("## Créer un compte")
        username = st.text_input("username (nouveau)")
        password = st.text_input("Mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password")
        col1, col2 = st.columns(2)
        submit = col1.form_submit_button("S'inscrire")
        cancel = col2.form_submit_button("Retour")

        if submit:
            if password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                user_data = register_user(username, password)
                if user_data:
                    st.success("Compte créé avec succès ✅")
                    st.session_state["authenticated"] = True
                    st.session_state["token"] = user_data["access_token"]
                    st.session_state["username"] = username
                    st.session_state["show_register"] = False
                    st.rerun()

        if cancel:
            st.session_state["show_register"] = False
            st.rerun()







@st.dialog("Modifier la conversation")
def edit_conversation(convo_id, title):
    new_title = st.text_input("Nouveau titre", value=title, key=f"edit_title_{convo_id}")
    delete = st.checkbox("Supprimer cette conversation", key=f"delete_{convo_id}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Valider", key=f"validate_{convo_id}"):
            if delete:
                st.toast(f"Conversation supprimée : {title}", icon="🗑️")
                # TODO: Supprimer la conversation de la base
            else:
                st.toast(f"Titre mis à jour : {new_title}", icon="✏️")
                # TODO: Mettre à jour le titre dans la base
            st.rerun()

    with col2:
        if st.button("Annuler", key=f"cancel_{convo_id}"):
            st.rerun()










st.set_page_config(page_title="Chatbot WAF", layout="wide")
# Initialisation
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# === Initialisation session_state ===
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "show_register" not in st.session_state:
    st.session_state["show_register"] = False

# === Affichage des modales ===
if not st.session_state["authenticated"]:
    if st.session_state["show_register"]:
        register_dialog()
    else:
        login_dialog()
    st.stop()

# Sélection du graphe
st.sidebar.title("Options")
selected_graph = st.sidebar.selectbox("Choisissez un graphe", ["UI tools", "Reasoning", "Basic"])

if st.sidebar.button("New Thread", key="new_thread"):
    new_thread()
# Liste des conversations
st.sidebar.markdown("### Threads")
conversations = get_threads()
if not conversations:
    print("No conversations found, creating a new thread", flush=True)
    # new_thread()

# État de la conversation sélectionnée
if "selected_conversation" not in st.session_state:
    st.session_state.selected_conversation = conversations[0]["id"]

for convo in conversations:
    col1, col2 = st.sidebar.columns([0.8, 0.2])
    if col1.button(convo["title"], key=convo["id"],use_container_width=True):
        st.session_state.selected_conversation = convo["id"]
        st.session_state.messages = get_thread_message(convo["id"])

    with col2:
        if st.button("⋮", key=f"menu_{convo['id']}"):
            # st.sidebar.write(f"Menu convo {convo['id']}")  # Placeholder pour menu contextuel
            edit_conversation(convo["id"], convo["title"])

# Affichage principal
st.title("Assistant de configuration WAF")






# Initialisation des messages
if "messages" not in st.session_state:
    st.session_state.messages = get_thread_message(st.session_state.selected_conversation)

# Affichage des messages
for msg in st.session_state.messages:
    if isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(msg.content)
    elif isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)

# Réponse à une nouvelle entrée utilisateur
if prompt := st.chat_input("Posez votre question ici..."):
    st.chat_message("user").markdown(prompt)
    msg = HumanMessage(content=prompt)
    st.session_state.messages.append(msg)

    payload = {"messages": [message_to_dict(msg)], "config":{"thread_id": st.session_state.selected_conversation}}

    with st.spinner("Analyse en cours..."):
        if selected_graph == "Basic":
            response = requests.post(BASIC_GRAPH, json=payload).json()
        elif selected_graph == "Reasoning":
            response = requests.post(REASONING_GRAPH, json=payload).json()
        elif selected_graph == "UI tools":
            response = requests.post(UI_GRAPH, json=payload).json()

        response_msg = AIMessage(
            content=response["messages"][-1]["content"],
            kwargs=response["messages"][-1]["additional_kwargs"]
        )
        with st.chat_message("assistant"):
            st.markdown(response_msg.content)
        st.session_state.messages.append(response_msg)


