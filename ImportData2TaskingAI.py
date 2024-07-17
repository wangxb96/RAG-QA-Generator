import requests
import json
from tqdm import tqdm
import math
import time

base_url = 'http://rag.bnuaifn.cn:9080/v1/'
api_key = 'tkEly3i7kGCSpUaHbM8JIavlptOl4Aed'   

headers = {"Authorization": f"Bearer {api_key}"}

def list_collections():
    response = requests.get(f"{base_url}collections", headers=headers)
    if response.status_code == 200:
        return response.json()['data']
    else:
        raise Exception(f"Failed to list collections: {response.text}")

def create_collection(name, embedding_model_id, capacity):
    data = {
        "name": name,
        "embedding_model_id": embedding_model_id,
        "capacity": capacity
    }
    response = requests.post(f"{base_url}collections", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['data']
    else:
        raise Exception(f"Failed to create collection: {response.text}")

def get_collection_details(collection_id):
    response = requests.get(f"{base_url}collections/{collection_id}", headers=headers)
    print(f"Get collection details response: {response.status_code} - {response.text}")
    if response.status_code == 200:
        return response.json()['data']
    else:
        raise Exception(f"Failed to get collection details: {response.text}")

def create_chunk(collection_id, content):
    data = {
        "collection_id": collection_id,
        "content": content
    }
    # 尝试不同的 API 端点
    endpoints = [
        f"{base_url}chunks",
        f"{base_url}collections/{collection_id}/chunks",
        f"{base_url}embeddings"
    ]
    for endpoint in endpoints:
        response = requests.post(endpoint, headers=headers, json=data)
        print(f"Create chunk response ({endpoint}): {response.status_code} - {response.text}")
        if response.status_code == 200:
            return response.json()['data']
    raise Exception(f"Failed to create chunk: All endpoints failed")

try:
    print("列出现有集合...")
    collections = list_collections()
    collection_ids = [collection['collection_id'] for collection in collections]
    print(f"现有集合 IDs: {collection_ids}")

    # 读取 BNUGPT_Optimized_qa_pair.json 文件
    with open('BNUGPT_Optimized_qa_pair_V3.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    qa_pairs = data['qa_pairs']
    total_records = len(qa_pairs)
    records_per_collection = 1000
    num_collections = math.ceil(total_records / records_per_collection)

    print(f"\n总记录数: {total_records}")
    print(f"每个集合的记录数: {records_per_collection}")
    print(f"需要创建的集合数: {num_collections}")

    for i in range(num_collections):
        print(f"\n创建集合 {i+1}/{num_collections}...")
        new_collection = create_collection(
            name=f"BNUGPT_Optimized_qa_pair_v3_part{i+1}",
            embedding_model_id="TpO9MbEa",
            capacity=records_per_collection
        )
        print(f"新创建的集合 ID: {new_collection['collection_id']}")

        # 获取并打印集合详情
        collection_details = get_collection_details(new_collection['collection_id'])
        print(f"集合详情: {json.dumps(collection_details, indent=2)}")

        start_index = i * records_per_collection
        end_index = min((i + 1) * records_per_collection, total_records)
        
        print(f"导入记录 {start_index+1} 到 {end_index}...")
        for j, qa_pair in enumerate(tqdm(qa_pairs[start_index:end_index], desc=f"Adding QA pairs to collection {i+1}")):
            content = f"{qa_pair['question']}\n{qa_pair['answer']}"
            try:
                chunk = create_chunk(
                    collection_id=new_collection['collection_id'],
                    content=content
                )
                # time.sleep(0.5)  # 每次请求后暂停0.5秒
            except Exception as e:
                print(f"Error creating chunk for QA pair {start_index + j + 1}: {str(e)}")
                print(f"QA pair content: {content[:100]}...")
                raise

    print("所有数据导入完成。")

except Exception as e:
    print(f"发生错误: {type(e).__name__}: {str(e)}")