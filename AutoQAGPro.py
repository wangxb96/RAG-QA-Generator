import streamlit as st
import requests
import tempfile
import os
from unstructured.partition.auto import partition
from openai import OpenAI

# 配置（请在使用时替换为实际的URL和API密钥）
base_url = 'YOUR_BASE_URL_HERE'
api_key = 'YOUR_API_KEY_HERE'
headers = {"Authorization": f"Bearer {api_key}"}

# OpenAI客户端配置（请在使用时替换为实际的API密钥和URL）
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
        st.error(f"调用API时发生错误: {e}")
        return None

def list_collections():
    try:
        response = requests.get(f"{base_url}collections", headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except requests.RequestException as e:
        st.error(f"获取集合列表失败: {e}")
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
        st.error(f"创建集合失败: {e}")
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
    st.error("创建chunk失败: 所有端点都失败了")
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
        st.error(f"处理文件时发生错误: {e}")
        return []
    finally:
        os.unlink(tmp_file_path)

@st.cache_data
def generate_qa_pairs_with_progress(text_chunks):
    qa_pairs = []
    progress_bar = st.progress(0)
    for i, chunk in enumerate(text_chunks):
        prompt = f"""基于以下给定的文本，生成一组高质量的问答对。请遵循以下指南：

            1. 问题部分：
            - 为同一个主题创建尽你所能多的（如K个）不同表述的问题。
            - 问题应涵盖文本中的关键信息和主要概念。
            - 使用多种提问方式，如直接询问、请求确认、寻求解释等。

            2. 答案部分：
            - 提供一个全面、信息丰富的答案，涵盖问题的所有可能角度。
            - 答案应直接基于给定文本，确保准确性。
            - 包含相关的细节，如日期、名称、职位等具体信息。

            3. 格式：
            - 使用"Q:"标记问题集合的开始，所有问题应在一个段落内。
            - 使用"A:"标记答案的开始。
            - 问答对之间用空行分隔。

            4. 内容要求：
            - 确保问答对紧密围绕文本主题。
            - 避免添加文本中未提及的信息。
            - 如果文本信息不足以回答某个方面，可以在答案中说明"根据给定信息无法确定"。

            示例结构（仅供参考，实际内容应基于给定文本）：

            Q: [问题1]？ [问题2]？ [问题3]？ ...... [问题K]？

            A: [全面、详细的答案，涵盖所有问题的角度]

            给定文本：
            {chunk}

            请基于这个文本生成问答对。
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
                    st.warning(f"无法解析响应: {response}")
            except Exception as e:
                st.warning(f"处理响应时出错: {str(e)}")
        
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
                content = f"问题：{qa_pair['question']}\n答案：{qa_pair['answer']}"
                if create_chunk(collection_id=collection_id, content=content):
                    success_count += 1
                else:
                    fail_count += 1
                    st.warning(f"插入QA对 {i+1} 失败")
            else:
                fail_count += 1
                st.warning(f"QA对 {i+1} 格式无效")
        except Exception as e:
            st.error(f"插入QA对 {i+1} 时发生错误: {str(e)}")
            fail_count += 1
        
        progress = (i + 1) / len(st.session_state.qa_pairs)
        progress_bar.progress(progress)
        status_text.text(f"进度: {progress:.2%} | 成功: {success_count} | 失败: {fail_count}")

    return success_count, fail_count

def main():
    st.set_page_config(page_title="RAG管理员界面", layout="wide")
    st.title("RAG管理员界面")

    # 初始化或更新 collections 列表
    if 'collections' not in st.session_state: #or st.sidebar.button("刷新Collections列表"):
        st.session_state.collections = list_collections()

    # 侧边栏
    st.sidebar.title("操作面板")
    operation = st.sidebar.radio("选择操作", ["上传文件", "管理知识库"])

    if operation == "上传文件":
        st.header("文件上传与QA对生成")
        uploaded_file = st.file_uploader("上传非结构化文件", type=["txt", "pdf", "docx"])
        
        if uploaded_file is not None:
            st.success("文件上传成功！")
            
            if st.button("处理文件并生成QA对"):
                with st.spinner("正在处理文件..."):
                    text_chunks = process_file(uploaded_file)
                    if not text_chunks:
                        st.error("文件处理失败，请检查文件格式是否正确。")
                        return
                    st.info(f"文件已分割成 {len(text_chunks)} 个文本段")

                with st.spinner("正在生成QA对..."):
                    st.session_state.qa_pairs = generate_qa_pairs_with_progress(text_chunks)
                    st.success(f"已生成 {len(st.session_state.qa_pairs)} 个QA对")

                if st.session_state.qa_pairs:
                    st.subheader("前3个QA对预览")
                    cols = st.columns(3)
                    for i, qa in enumerate(st.session_state.qa_pairs[:3]):
                        with st.expander(f"**QA对 {i + 1}**", expanded=True):
                            st.markdown("**问题:**")
                            st.markdown(qa['question'])
                            st.markdown("**答案:**")
                            st.markdown(qa['answer'])
                        st.markdown("---") 

    elif operation == "管理知识库":
        st.header("知识库管理")
        option = st.radio("选择操作", ("插入现有Collection", "创建新Collection"))
        
        if 'collections' not in st.session_state:
            st.session_state.collections = list_collections()
        
        if option == "插入现有Collection":
            if st.session_state.collections:
                collection_names = [c['name'] for c in st.session_state.collections]
                selected_collection = st.selectbox("选择Collection", collection_names)
                selected_id = next(c['collection_id'] for c in st.session_state.collections if c['name'] == selected_collection)
            else:
                st.warning("没有可用的 Collections，请创建新的 Collection。")
                option = "创建新Collection"

        if option == "创建新Collection":
            new_collection_name = st.text_input("输入新Collection名称")
            capacity = st.number_input("设置Collection容量", min_value=1, max_value=1000, value=1000)
            if st.button("创建新Collection"):
                with st.spinner("正在创建新Collection..."):
                    new_collection = create_collection(
                        name=new_collection_name,
                        embedding_model_id="TpO9MbEa",
                        capacity=capacity
                    )
                    if new_collection:
                        st.success(f"新Collection创建成功，ID: {new_collection['collection_id']}")
                        # 立即更新 collections 列表
                        st.session_state.collections = list_collections()
                        st.rerun()
                    else:
                        st.error("创建新Collection失败")
        
        # 插入QA对到选定的Collection
        if hasattr(st.session_state, 'qa_pairs') and st.session_state.qa_pairs:
            if st.button("插入QA对到选定的Collection"):
                if 'selected_id' in locals():
                    with st.spinner("正在插入QA对..."):
                        success_count, fail_count = insert_qa_pairs_to_database(selected_id)
                        st.success(f"数据插入完成！总计: {len(st.session_state.qa_pairs)} | 成功: {success_count} | 失败: {fail_count}")
                else:
                    st.warning("请先选择或创建一个 Collection")
        else:
            st.warning("没有可用的QA对。请先上传文件并生成QA对。")

if __name__ == "__main__":
    main()