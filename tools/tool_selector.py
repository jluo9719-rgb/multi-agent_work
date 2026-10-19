import chromadb
from tools.tool_definitions import TOOLS
from rag.knowledge_base import embedder   #复用已加载的embedder，不需要重新加载

#模块加载时初始化
tool_client =chromadb.PersistentClient(path="./chroma_db")
tool_collection = tool_client.get_or_create_collection(name ="tool")
description_to_schema = {}

if tool_collection.count() ==0:
    all_description = []
    for tool in TOOLS:
        desc = tool["description"]
        description_to_schema[desc] =tool
        all_description.append(desc)
    vectors = embedder.encode(all_description)
    tool_collection.add(
        documents = all_description,
        embeddings = vectors,
        ids =[f"tool_{i}" for i in range(len(all_description))],
    )
else:
    for tool in TOOLS:
        description_to_schema[tool["description"]] =tool

def select_tools(query : str,top_n :int=2) -> list:
    query_vectors = embedder.encode([query]) 
    result = tool_collection.query(query_embeddings =query_vectors,n_results =top_n)
    result_doc = result['documents'][0]
    selected_tools =[]
    for desc in result_doc:
        try:
            selected_tools.append(description_to_schema[desc])
        except KeyError:
            return []
    return selected_tools