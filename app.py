import streamlit as st
from google import genai
from google.genai import types
import os

# --- Configuração Inicial ---
st.set_page_config(layout="centered")
st.title("📱 Chatbot Editável (Gemini Flash)")

# 1. Tenta inicializar o cliente Gemini lendo a chave da variável de ambiente
# O Streamlit Cloud injeta a chave neste local (os.environ)
API_KEY = os.environ.get('GEMINI_API_KEY')

try:
    if not API_KEY:
        st.error("ERRO: A GEMINI_API_KEY não foi configurada nos Segredos (Secrets) do Streamlit Cloud.")
        st.stop()
        
    client = genai.Client(api_key=API_KEY)
except Exception:
    st.error("ERRO: Falha na inicialização do cliente Gemini. Verifique se a chave é válida.")
    st.stop()

# 2. Definição do Modelo
MODEL_NAME = "gemini-2.5-flash"

# --- Gerenciamento de Estado (Histórico da Conversa) ---

if "messages" not in st.session_state:
    st.session_state.messages = []
if "editing" not in st.session_state:
    st.session_state.editing = False

def get_history_for_api():
    """Formata o histórico de mensagens para a API do Gemini."""
    api_history = []
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "model"]:
            api_history.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(msg["content"])]
                )
            )
    return api_history

def update_and_save_edit():
    """Salva a edição feita pelo usuário e desativa o modo de edição."""
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "model":
        last_message = st.session_state.messages[-1]
        last_message["content"] = st.session_state.edited_text
        last_message["edited"] = True
    
    st.session_state.editing = False
    st.session_state.edited_text = ""
    st.rerun()

# --- Exibir Histórico ---

for message in st.session_state.messages:
    if message["role"] in ["user", "model"]:
        with st.chat_message(message["role"]):
            if message["role"] == "model" and message.get("edited", False):
                st.markdown(f'*{message["content"]}* **(EDITADO)**')
            else:
                st.markdown(message["content"])

# --- Lógica de Chat ---

if not st.session_state.editing:
    if prompt := st.chat_input("Diga algo..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("model"):
            with st.spinner("Gerando resposta..."):
                api_history = get_history_for_api()
                api_history.append(types.Content(role="user", parts=[types.Part.from_text(prompt)]))

                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=api_history,
                    )
                    gemini_response_text = response.text
                    
                    st.session_state.messages.append({
                        "role": "model",
                        "content": gemini_response_text,
                        "edited": False
                    })
                    
                    st.session_state.editing = True
                    st.session_state.edited_text = gemini_response_text
                    
                    st.markdown(gemini_response_text)
                    st.rerun() 
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro na API: {e}")
                    st.session_state.messages.pop()

# --- Interface de Edição ---
if st.session_state.editing:
    st.divider()
    st.subheader("📝 Edite a Resposta do Assistente")
    st.caption("Ajuste o texto e clique em salvar para que o Gemini use esta versão no próximo turno.")
    
    st.text_area(
        label="Texto para Edição:",
        value=st.session_state.edited_text,
        key="edited_text",
        height=200
    )
    
    st.button("✅ Salvar Edição e Continuar", on_click=update_and_save_edit)