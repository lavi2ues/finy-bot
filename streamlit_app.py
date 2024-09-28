import streamlit as st
from openai import OpenAI
from tempfile import NamedTemporaryFile
import time

# Show title and description.
st.title("💬 Personal Finance Teller")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
)

@st.fragment
def saveFileOpenAI(location, client):
            file = client.files.create(file = location, purpose = 'assistants')
            return file.id

def createVectorStore(file_id, client):
    vector = client.beta.vector_stores.create(
        file_ids=file_id
    )
    return vector.id

def startBotCreation(file_id, client):
    assistant = client.beta.assistants.create(
            instructions="You are a knowledge assistant, Use your knowledge base to best respond to queries",
            name="FileAssistant",
            model="gpt-4o",
            tools =[{"type": "file_search"}],
            tool_resources= {
                "file_search": {
                "vector_store_ids": [file_id]
                }
            },
        )
    return assistant.id


def get_run_status(thread_id, run_id, client):
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    return run.status

def input_section():
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.", icon="🗝️")
    else:
        # Create an OpenAI client.
        client = OpenAI(api_key=openai_api_key)

        uploaded_files = st.file_uploader(
            "Select your files for the month (pdf only)", accept_multiple_files=True
        )
        files = []
        for uploaded_file in uploaded_files:
            st.write("filename:", uploaded_file.name)
            with NamedTemporaryFile(dir='.', suffix='.pdf') as f:
                f.write(uploaded_file.getbuffer())
                file = client.files.create(file = open(f.name, "rb"), purpose = 'assistants')
                fileID = file.id
                files.append(fileID)
        if(len(files) >= 1):
            st.write(files)
            identify_param = " , ".join(str(e) for e in files)
            with st.chat_message("assistant"):
                st.markdown("Your files have been uploaded with IDs : "+ identify_param)

            st.write(uploaded_files)

            vectorID = createVectorStore(files, client)
            st.write(vectorID)

            assistantID = startBotCreation(vectorID, client)
            with st.chat_message("assistant"):
                    st.markdown("I am ready to assist you and I identify as "+ assistantID)
        obj = {}
        obj['assistant'] = assistantID
        obj['client'] = client
        return obj

def startThreadCreation(prompt, client):
        messages = [{"role":"user", "content": prompt}]
        thread = client.beta.threads.create(messages = messages)
        return thread
    
def run_assistant(thread_id, assistant_id, client):
    run = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id
    )
    return run


def get_newest_message(thread_id, client):
    thread_messages = client.beta.threads.messages.list(thread_id)
    list_message = thread_messages.data[0]
    response = list_message.content[0].text.value
    return response

@st.fragment
def chat_section(assistantID, client):
    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("What would you like to know today?"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})        

        userThread = startThreadCreation(prompt, client)

        with st.chat_message("user"):
            st.markdown(prompt)
        # Generate a response using the OpenAI API.

        run = run_assistant(userThread.id, assistantID, client)
        while run.status != "completed":
            run.status = get_run_status(userThread.id, run.id, client)
            time.sleep(1)

        response = get_newest_message(userThread.id, client)

        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            reply = st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.write(userThread.id)
        st.write(assistantID)
    return userThread

obj = input_section()
if(obj is not None):
    userThread = chat_section(obj['assistant'], obj['client'])
