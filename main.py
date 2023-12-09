import streamlit as st
import openai
from flask import Flask, jsonify, make_response
from flask_cors import CORS  # Import CORS extension

# Create a Flask app for CORS handling
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes in the app


openai.api_key = ""

# load from txt file
job_scope_file_path = 'job_scope.txt'
company_profile_file_path = 'company_profile.txt'
resources_list_file_path = 'resources_list.txt'
buddy_list_file_path = 'buddy_lisy.txt'

# Open the file in read mode
with open(job_scope_file_path, 'r') as file:
    # Read the contents of the file into a variable
    job_scope = file.read()
with open(company_profile_file_path, 'r') as file:
    # Read the contents of the file into a variable
    company_profile = file.read()
with open(resources_list_file_path, 'r') as file:
    # Read the contents of the file into a variable
    resources_list = file.read()
with open(buddy_list_file_path, 'r') as file:
    # Read the contents of the file into a variable
    buddy_list = file.read()

# start streamlit app
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Hi, how can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)

    with st.spinner("Give me a second..."):
        #get question 
        query = prompt

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role":"system", "content":f"""You are now an assistant admin for new employees that knows everything about Bank X, you need to give answer only from knowledge bank else just answer sorry you dont know.
                If you dont know, you can give the contact person from the resources given
                If the employee ask on any suggestion, you can give the suggestion but based on the knowledge bank. Give the answers in point if necessary. 
                Knowledge bank:
                1. Company profile: {company_profile}
                2. Role & responsibilities: {job_scope}
                3. Resources: {resources_list}
                4. Mentor List: {buddy_list}
                """},

                {"role":"user", "content":str(prompt)}
            ],
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        print("response: " + str(response['choices'][0]['message']['content']))
    with st.chat_message("assistant"):
        st.markdown(response['choices'][0]['message']['content'])
    st.session_state.messages.append({"role": "assistant", "content": response['choices'][0]['message']['content']})


# Run the Streamlit app
if __name__ == "__main__":
    app.run(port=st.get_option("server.port", 8501), host=st.get_option("server.address", "0.0.0.0"))