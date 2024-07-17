# RAG-QA-Generator
[中文版本](README-CN.md)
## Project Overview
RAG-QA-Generator is an automated knowledge base construction and management tool designed for Retrieval-Augmented Generation (RAG) systems. It processes document data, leverages large language models to generate high-quality question-answer pairs (QA pairs), and stores this data in a database, enabling automated construction and management of RAG system knowledge bases.

![](/Figure/RAG管理主页面.png)
## Features
- Support for multiple document formats (txt, pdf, docx)
- AI-powered generation of high-quality QA pairs
- Intuitive web interface for file upload and knowledge base management
- Flexible collection management system
- Real-time progress tracking and error handling

## Tech Stack
- Python 3.7+
- Streamlit
- OpenAI API (qwen1.5-72b model)
- unstructured library
- RESTful API

### Installation
- Clone the repository:
```
git clone https://github.com/yourusername/RAG-QA-Generator.git
cd RAG-QA-Generator
```
- Install dependencies:
```
pip install -r requirements.txt
``` 
- Configure API:
```
base_url = 'http://your-api-url/v1/'
api_key = 'your-api-key'
headers = {"Authorization": f"Bearer {api_key}"}

client = OpenAI(
    api_key="your-openai-api-key",
    base_url="http://your-openai-api-url/v1",
)
```

### Usage
- Start the application:
```
streamlit run app.py
```
- Access http://localhost:8501
- Use the interface to upload files, generate QA pairs, and manage the knowledge base.

## Project Structure

This project consists of the following main components:

### Code Files

1. **AutoQAGPro.py**
   This is the core file of the project, containing the main functionalities of the entire RAG system:
   - File upload and processing
   - QA pair generation using AI model (qwen1.5-72b)
   - Knowledge base collection creation and management
   - Data insertion into TaskingAI database
   - Streamlit-based user interface

2. **ImportData2TaskingAI.py**
   This script is used to import data into the TaskingAI database. It likely includes functions for connecting to the database, reading JSON files, and inserting data.

### Datasets

1. **BNUGPT_Optimized_qa_pair_V3.json**
   This is an optimized question-answer pair dataset stored in JSON format. It can be imported into the TaskingAI database using the ImportData2TaskingAI.py script, providing a foundation of knowledge for the RAG system.

2. **testdata.txt**
   This is a test file used for generating QA pairs. It contains sample texts from various topics or domains, used to test and validate the QA pair generation functionality of AutoQAGPro.py.

### RAG Database System
While not a specific file, [TaskingAI](https://github.com/TaskingAI/TaskingAI) is the database system used in this project. It is specially designed for storing and managing knowledge bases for RAG systems, supporting efficient data storage, retrieval, and vectorization operations.

### Contributing
Issues and pull requests are welcome. 
