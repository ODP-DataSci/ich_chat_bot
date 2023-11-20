import streamlit as st
from streamlit_chat import message
from streamlit_extras.colored_header import colored_header
#from langchain.document_loaders import UnstructuredPDFLoader
#from langchain.indexes import VectorstoreIndexCreator
#from detectron2.config import get_cfg
import csv
import os
import openai
import time
from packaging import version

#cfg = get_cfg()    
#cfg.MODEL.DEVICE = 'cpu' #GPU is recommended


required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)

if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {openai.__version__}"
                     " is less than the required version 1.1.1")
else:
    print("OpenAI version is compatible.")

# -- Now we can get to it
from openai import OpenAI

os.environ["ORGANIZATION_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

client = OpenAI(
  organization=os.environ["ORGANIZATION_KEY"],
  api_key=os.environ["OPENAI_API_KEY"],
)

st.set_page_config(page_title="ICH Guidelines Chat")


def list_assistants():

    assistant_object = client.beta.assistants.list()
    return assistant_object

def select_assistant(assistant_id):
    # Use the 'beta.assistants' attribute, not 'Assistant'
    assistant = client.beta.assistants.retrieve(assistant_id)
    return assistant.id

def update_assistant(assistant_id, file_ids):
    assistant = client.beta.assistants.update(assistant_id, file_ids=file_ids)
    return assistant.id

def create_assistant(name, instructions, tools, model):
    assistant = client.beta.assistants.create(
        name=name,
        instructions=instructions,
        tools=tools,
        model=model
    )
    return assistant.id  # Return the assistant ID

def get_assistant_by_id(assistant_id):
    assistant = client.beta.assistants.retrieve(assistant_id)
    return assistant.id

def create_thread():
    
    thread = client.beta.threads.create()
    return thread

def generate_response(thread, user_input):
    """
    Function designed to generate the next response from a chat history containing messages from
    both the user and the agent.
    Parameters
    ----------
    `thread` : Open AI Thread Object
        History of conversation.
    `user_input` : String
        Current User question.
    Return
    ------
    `message` : str
        The latest response from the model.
    """
    file_ids = st.session_state.files
    assistant_id = st.session_state.assistant

    message_return = ""
    file_lists = [file_ids[:20],file_ids[20:40],file_ids[40:]]
    response_divider = ["Response for files 1-20\n\n", "Response for files 20-40\n\n", "Response for files 40-50\n\n"]
    
    for i in [0,1,2]:
        message_return += response_divider[i]
        assistant_id = update_assistant(assistant_id, file_lists[i])
        message_obj = client.beta.threads.messages.create(
            thread_id = thread.id,
            role = "user",
            content = user_input
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id,
            instructions="Please address the user as Kosi."
        )

        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        run_status = run.status 
        while True:
            if run_status in ["completed", 'failed']:
                break
            time.sleep(1)
            run_status = run.status 

        message_obj = client.beta.threads.messages.list(
            thread_id= thread.id
        )
        
        message_return += message_obj.data[0].content[0].text.value
            
    return message_return

def get_text():
    """
    Function to fetch the user's input from the text box.
    Return
    -------
    `input_text` : str
        The user's input.
    """
    input_text = st.text_input("Input prompt here: ", "", key="input") #Free text input field
    return input_text


if 'generated' not in st.session_state:
    st.session_state['generated'] = [] #Used to store the agent's responses

if 'past' not in st.session_state:
    st.session_state['past'] = [] #Used to store the user's prompts

if 'files' not in st.session_state:
    file = open("file_ids.csv", "r")
    data = list(csv.reader(file, delimiter=","))
    file.close()
    st.session_state['files'] = data

if 'thread' not in st.session_state and ('OpenAIPass' in st.secrets) and ('OrganizationPass' in st.secrets):
    thread = create_thread()
    st.session_state['thread'] = thread.id

if 'assistant' not in st.session_state and ('OpenAIPass' in st.secrets) and ('OrganizationPass' in st.secrets):
    assistant = get_assistant_by_id('asst_5jdAAajRyTLPX7r3pLC3YAlK')
    st.session_state['assistant'] = assistant

with st.sidebar:
    st.title('ICH Guidelines Chat')
    if ('OpenAIPass' in st.secrets):
        st.success('Open AI Key already provided!', icon='✅')
        hf_pass = st.secrets['OpenAIPass']
        os.environ["OPENAI_API_KEY"] = hf_pass
    else:
        hf_pass = st.text_input('Enter Open AI Key:', type='password')
        if not (hf_pass):
            st.warning('Please enter Open AI Key!', icon='⚠️')
        else:
            os.environ["OPENAI_API_KEY"] = hf_pass
            
            
    if ('OrganizationPass' in st.secrets):
        st.success('Open AI Organization Key already provided!', icon='✅')
        organize_key = st.secrets['OrganizationPass']
        os.environ["ORGANIZATION_KEY"] = organize_key
    else:
        organize_key = st.text_input('Enter Open AI Organization Key:', type='password')
        if not (organize_key):
            st.warning('Please enter Open AI Organization Key!', icon='⚠️')
        else:
            os.environ["ORGANIZATION_KEY"] = organize_key
            if (hf_pass):
                st.success('Proceed to entering your prompt message!', icon='👉')


input_container = st.container()
colored_header(label='', description='', color_name='blue-30')
response_container = st.container()


with input_container:
    user_input = get_text()

with response_container:
    if user_input:
        st.session_state.past.append(user_input) #Add user input to storage
        response = generate_response(st.session_state.thread, user_input)
        st.session_state.generated.append(response) #Add model output to storage
        
    if st.session_state['generated']:
        for i in range(len(st.session_state['generated'])):
            message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')
            message(st.session_state["generated"][i], key=str(i))