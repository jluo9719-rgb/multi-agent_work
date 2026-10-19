#工具定义
from pydantic import BaseModel,Field

class RagInput(BaseModel):
    query: str = Field(description="用户想要检索的公司内部问题")

class SearchInput(BaseModel):
    query: str = Field(description="搜索关键词，应包含完整的问题信息以提高搜索准确性")

TOOLS =[
    {
        "name":"retrieve_company_docs",
        "description":"检索公司内部控制手册等内部文档。当用户询问公司制度、流程、规定相关问题时使用。",
        "input_schema":RagInput.model_json_schema()
    },
    {
        "name": "search_google",
        "description": "通用网络搜索。当需要实时信息（天气、新闻、股票）、百科常识，或内部文档中没有答案时使用。",
        "input_schema": SearchInput.model_json_schema(),
    },
]
