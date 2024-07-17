import streamlit as st
import requests
import tempfile
import os
from unstructured.partition.auto import partition
from openai import OpenAI

# Configuration (please replace with actual URL and API key when using)
base_url = 'YOUR_BASE_URL_HERE'
api_key = 'YOUR_API_KEY_HERE'
headers = {"Authorization": f"Bearer {api_key}"}

# OpenAI client configuration (please replace with actual API key and URL when using)
client = OpenAI(
    api_key="YOUR_OPENAI_API_KEY_HERE",
    base_url="YOUR_OPENAI_BASE_URL_HERE",
)

#@st.cache_data
def get_completion(prompt, model="qwen1.5-72b"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling API: {e}")
        return None

def list_collections():
    try:
        response = requests.get(f"{base_url}collections", headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except requests.RequestException as e:
        st.error(f"Failed to get collection list: {e}")
        return []

def create_collection(name, embedding_model_id, capacity):
    data = {
        "name": name,
        "embedding_model_id": embedding_model_id,
        "capacity": capacity
    }
    try:
        response = requests.post(f"{base_url}collections", headers=headers, json=data)
        response.raise_for_status()
        return response.json()['data']
    except requests.RequestException as e:
        st.error(f"Failed to create collection: {e}")
        return None

def create_chunk(collection_id, content):
    data = {
        "collection_id": collection_id,
        "content": content
    }
    endpoints = [
        f"{base_url}chunks",
        f"{base_url}collections/{collection_id}/chunks",
        f"{base_url}embeddings"
    ]
    for endpoint in endpoints:
        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['data']
        except requests.RequestException:
            continue
    st.error("Failed to create chunk: All endpoints failed")
    return None

def process_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    try:
        elements = partition(filename=tmp_file_path)
        text_chunks = [str(element) for element in elements if not str(element).strip() == '']
        return text_chunks
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return []
    finally:
        os.unlink(tmp_file_path)

@st.cache_data
def generate_qa_pairs_with_progress(text_chunks):
    qa_pairs = []
    progress_bar = st.progress(0)
    for i, chunk in enumerate(text_chunks):
        prompt = f"""Based on the following given text, generate a set of high-quality question-answer pairs. Please follow these guidelines:

        1. Question part:
        - Create as many different phrasings of questions (e.g., K questions) as you can for the same topic.
        - Questions should cover key information and main concepts in the text.
        - Use various questioning methods, such as direct inquiries, requests for confirmation, seeking explanations, etc.

        2. Answer part:
        - Provide a comprehensive, informative answer that covers all possible angles of the questions.
        - The answer should be directly based on the given text, ensuring accuracy.
        - Include relevant details such as dates, names, positions, and other specific information.

        3. Format:
        - Use "Q:" to mark the beginning of the question set, all questions should be in one paragraph.
        - Use "A:" to mark the beginning of the answer.
        - Separate question-answer pairs with a blank line.

        4. Content requirements:
        - Ensure that the question-answer pairs closely revolve around the text's topic.
        - Avoid adding information not mentioned in the text.
        - If the text information is insufficient to answer a certain aspect, you can state "Cannot be determined based on the given information" in the answer.

        Example structure (for reference only, actual content should be based on the given text):

        Q: [Question 1]? [Question 2]? [Question 3]? ...... [Question K]?

        A: [Comprehensive, detailed answer covering all angles of the questions]

        Given text:
        {chunk}

        Please generate question-answer pairs based on this text.
        """
        response = get_completion(prompt)
        if response:
            try:
                parts = response.split("A:", 1)
                if len(parts) == 2:
                    question = parts[0].replace("Q:", "").strip()
                    answer = parts[1].strip()
                    qa_pairs.append({"question": question, "answer": answer})
                else:
                    st.warning(f"Unable to parse response: {response}")
            except Exception as e:
                st.warning(f"Error processing response: {str(e)}")
        
        progress = (i + 1) / len(text_chunks)
        progress_bar.progress(progress)
    
    return qa_pairs

def insert_qa_pairs_to_database(collection_id):
    progress_bar = st.progress(0)
    status_text = st.empty()
    success_count = 0
    fail_count = 0
    for i, qa_pair in enumerate(st.session_state.qa_pairs):
        try:
            if "question" in qa_pair and "answer" in qa_pair:
                content = f"Question: {qa_pair['question']}\nAnswer: {qa_pair['answer']}"
                if create_chunk(collection_id=collection_id, content=content):
                    success_count += 1
                else:
                    fail_count += 1
                    st.warning(f"Failed to insert QA pair {i+1}")
            else:
                fail_count += 1
                st.warning(f"QA pair {i+1} has invalid format")
        except Exception as e:
            st.error(f"Error inserting QA pair {i+1}: {str(e)}")
            fail_count += 1
        
        progress = (i + 1) / len(st.session_state.qa_pairs)
        progress_bar.progress(progress)
        status_text.text(f"Progress: {progress:.2%} | Success: {success_count} | Failed: {fail_count}")

    return success_count, fail_count

def main():
    st.set_page_config(page_title="RAG Admin Interface", layout="wide")
    st.title("RAG Admin Interface")

    # Initialize or update collections list
    if 'collections' not in st.session_state:
        st.session_state.collections = list_collections()

    # Sidebar
    st.sidebar.title("Operation Panel")
    operation = st.sidebar.radio("Select Operation", ["Upload File", "Manage Knowledge Base"])

    if operation == "Upload File":
        st.header("File Upload and QA Pair Generation")
        uploaded_file = st.file_uploader("Upload Unstructured File", type=["txt", "pdf", "docx"])
        
        if uploaded_file is not None:
            st.success("File uploaded successfully!")
            
            if st.button("Process File and Generate QA Pairs"):
                with st.spinner("Processing file..."):
                    text_chunks = process_file(uploaded_file)
                    if not text_chunks:
                        st.error("File processing failed. Please check if the file format is correct.")
                        return
                    st.info(f"File has been split into {len(text_chunks)} text segments")

                with st.spinner("Generating QA pairs..."):
                    st.session_state.qa_pairs = generate_qa_pairs_with_progress(text_chunks)
                    st.success(f"Generated {len(st.session_state.qa_pairs)} QA pairs")

                if st.session_state.qa_pairs:
                    st.subheader("Preview of First 3 QA Pairs")
                    cols = st.columns(3)
                    for i, qa in enumerate(st.session_state.qa_pairs[:3]):
                        with st.expander(f"**QA Pair {i + 1}**", expanded=True):
                            st.markdown("**Question:**")
                            st.markdown(qa['question'])
                            st.markdown("**Answer:**")
                            st.markdown(qa['answer'])
                        st.markdown("---") 

    elif operation == "Manage Knowledge Base":
        st.header("Knowledge Base Management")
        option = st.radio("Select Operation", ("Insert into Existing Collection", "Create New Collection"))
        
        if 'collections' not in st.session_state:
            st.session_state.collections = list_collections()
        
        if option == "Insert into Existing Collection":
            if st.session_state.collections:
                collection_names = [c['name'] for c in st.session_state.collections]
                selected_collection = st.selectbox("Select Collection", collection_names)
                selected_id = next(c['collection_id'] for c in st.session_state.collections if c['name'] == selected_collection)
            else:
                st.warning("No available Collections. Please create a new Collection.")
                option = "Create New Collection"

        if option == "Create New Collection":
            new_collection_name = st.text_input("Enter New Collection Name")
            capacity = st.number_input("Set Collection Capacity", min_value=1, max_value=1000, value=1000)
            if st.button("Create New Collection"):
                with st.spinner("Creating new Collection..."):
                    new_collection = create_collection(
                        name=new_collection_name,
                        embedding_model_id="TpO9MbEa",
                        capacity=capacity
                    )
                    if new_collection:
                        st.success(f"New Collection created successfully, ID: {new_collection['collection_id']}")
                        # Immediately update collections list
                        st.session_state.collections = list_collections()
                        st.rerun()
                    else:
                        st.error("Failed to create new Collection")
        
        # Insert QA pairs into selected Collection
        if hasattr(st.session_state, 'qa_pairs') and st.session_state.qa_pairs:
            if st.button("Insert QA Pairs into Selected Collection"):
                if 'selected_id' in locals():
                    with st.spinner("Inserting QA pairs..."):
                        success_count, fail_count = insert_qa_pairs_to_database(selected_id)
                        st.success(f"Data insertion complete! Total: {len(st.session_state.qa_pairs)} | Success: {success_count} | Failed: {fail_count}")
                else:
                    st.warning("Please select or create a Collection first")
        else:
            st.warning("No QA pairs available. Please upload a file and generate QA pairs first.")

if __name__ == "__main__":
    main()