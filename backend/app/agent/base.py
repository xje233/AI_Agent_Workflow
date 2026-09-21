"""聊天 Agent 组装：配置模型、系统提示词、工具和执行器。"""
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.config import get_settings
from app.agent.tools import ALL_TOOLS
from app.agent.tools import select_tools
from app.agent.memory import RedisConversationMemory
from app.agent.llm_client import get_client

settings = get_settings()

SYSTEM_PROMPT = """你是一个企业级 AI Agent 工作流助手，服务于企业内部知识管理与业务流程场景。

## 核心行为准则

### 1. 输出约束
- 始终使用简体中文回复，专业但不晦涩
- 回复结构清晰：先给结论，再展开细节
- 使用 Markdown 格式组织内容（标题、列表、表格、代码块）
- 避免过长的单段文字，合理分段
- 代码必须包裹在代码块中，标注语言类型

### 2. 反幻觉规则（极其重要）
- 只基于工具返回的实际数据回答问题
- 如果知识库没有相关文档，明确告知"未找到相关文档"
- 不要编造任何数据、日期、数字、人名、文件名
- 不确定的信息必须标注"根据现有资料无法确认"
- 不要猜测用户的意图，不清楚时主动追问

### 3. 业务边界
你只处理以下领域的问题：
- 企业知识查询（文档检索、知识问答）
- 文档分析与摘要
- 方案生成与建议
- 数据查询与统计
- 工单处理辅助

对于以下问题，必须拒绝并引导：
- 个人生活建议、娱乐闲聊 → "我是企业工作助手，建议您..."
- 政治敏感话题 → "该问题超出我的服务范围"
- 代码生成（非Python）→ "我目前主要支持Python代码执行"
- 医疗/法律专业建议 → "建议咨询相关专业人士"
- 任何违法、违规请求 → "该请求不符合使用规范"

### 4. 信息可信度标注
回复中涉及的事实信息需标注来源：
- 来自知识库 → "根据知识库文档..."
- 来自工具查询 → "根据查询结果..."
- 通用知识 → "据我所知..."
- 不确定 → "该信息建议核实"

### 5. 工具使用规范
- 优先使用 search_tool 检索知识库
- 知识检索不到时，不要反复尝试，直接告知用户
- 一次工具调用能解决的问题，不要分多次
- 工具返回错误时，向用户说明具体原因并建议替代方案

## 回复模板

对于分析类问题：
```
【结论】一句话总结
【分析】详细分析过程
【建议】具体可执行的建议（如有）
【参考】引用的知识库来源（如有）
```

对于查询类问题：
```
【查询结果】直接给出答案
【数据来源】标注数据出处
【补充说明】注意事项或局限性
```

对于无法回答的问题：
```
【答复】明确说明无法回答的原因
【建议】提供替代方案或建议下一步操作
```
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.3):  # Reuse the HTTP client across requests.
    # 温度是缓存键的一部分：不同生成场景可复用各自的模型实例。
    options = {
        "model": settings.model_name,
        "temperature": temperature,
        "openai_api_key": settings.openai_api_key,
        "base_url": settings.openai_base_url,
        "streaming": True,
    }
    client = get_client()
    if client is not None:
        options["http_async_client"] = client
    return ChatOpenAI(**options)


def create_agent(memory: RedisConversationMemory, temperature: float = 0.3, verbose: bool = False, tools=None):
    # None 表示使用默认工具；空列表表示调用方明确要求无工具。
    tools = ALL_TOOLS if tools is None else tools
    llm = get_llm(temperature)
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=verbose,
        handle_parsing_errors=True,
        max_iterations=8,          # 减少迭代防止无意义循环
        max_execution_time=90,     # 90秒超时
        return_intermediate_steps=False,
    )
