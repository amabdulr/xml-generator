"""
Helper functions for the Streamlit app
Contains all the business logic and agent operations

ANALOGY: Think of this module as the "ENGINE ROOM" of a ship 🚢
- streamlit_app.py is the BRIDGE (controls and displays)
- app_functions.py is the ENGINE ROOM (does all the heavy work)
- first_draft_tab.py is a SPECIALIZED DECK (handles specific operations)

The captain (user) gives orders on the bridge, but all the power and processing
happens down in the engine room where the real work gets done.

FUNCTIONS OVERVIEW:
├── get_product_info()      : 🔍 RAG search tool - Queries vector database for product documentation
├── run_agent()             : 🤖 AI Agent orchestrator - Runs LangChain agent with tools and prompts
├── format_output()         : 📋 Output formatter - Converts agent responses to readable markdown
└── apply_prompt_file()     : 📝 Prompt template engine - Reads .md files and populates placeholders

This module handles:
- Vector database queries (Chroma + HuggingFace embeddings)
- LangChain agent execution (OpenAI Functions Agent)
- LLM invocations (via utils.get_llm())
- Template-based prompt generation
"""

from typing import List
from langchain.agents import (
    AgentExecutor,
    OpenAIFunctionsAgent,
    create_openai_functions_agent,
)
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers.self_query.base import SelfQueryRetriever
from utils import get_llm
import streamlit as st


@tool
def get_product_info(product: str, query: str) -> List[Document]:
    """given a Cisco product name and a query, return the product context
    Args:
        product: Cisco product name. Valid products are: "firepower", "sdwan", "pickle_fish", "9800"
        query: user query about the product
    """
    metadata_field_info = [
        AttributeInfo(
            name="source",
            description="The source file the information came from",
            type="string",
        ),
        AttributeInfo(
            name="product",
            description='Cisco product name. Valid products are: "firepower", "sdwan", "pickle_fish", "9800"',
            type="string",
        ),
    ]
    document_content_description = "Cisco Product information"
    llm = get_llm()
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = Chroma(
        collection_name="cisco_products_custom_loader",
        persist_directory="data/cisco_products_custom_loader",
        embedding_function=embeddings,
    )
    retriever = SelfQueryRetriever.from_llm(
        llm,
        vectorstore,
        document_content_description,
        metadata_field_info,
        enable_limit=True,
        verbose=True,
    )

    result = retriever.invoke(f"Product: {product}\nQuery: {query}")

    return result


def run_agent(product_name: str, question: str, rca_content: str):
    """Run the agent with the given inputs"""
    
    # Append RCA content to the question
    full_question = question + rca_content
    
    product_version_prompt_template = """
    given a Cisco product name and a question from a user, return the answer.
    Use your tools to fetch context to answer the question to provide a more accurate answer.
    Cisco product: {product_name}
    question: {question}
    answer:
    """

    product_prompt_template = PromptTemplate(
        input_variables=["product_name", "question"],
        template=product_version_prompt_template,
    )

    llm = get_llm()

    prompt = OpenAIFunctionsAgent.create_prompt()
    agent = create_openai_functions_agent(
        llm=llm, tools=[get_product_info], prompt=prompt
    )

    agent_executor = AgentExecutor(
        agent=agent, tools=[get_product_info], verbose=False, stream_runnable=False
    )
    
    res = agent_executor.invoke(
        input={
            "input": product_prompt_template.format_prompt(
                product_name=product_name,
                question=full_question,
            )
        }
    )

    return res


def format_output(result: dict) -> str:
    """Format the agent output in a readable way"""
    if 'output' in result:
        output_text = result['output']
        
        # Format the output with markdown
        formatted = f"""## 📋 Documentation Recommendation

{output_text}

---
### 🔍 Query Details
**Product:** {st.session_state.product_name}
**Status:** ✅ Analysis Complete
"""
        return formatted
    return "No output received from agent."


def apply_prompt_file(prompt_file_path: str, rca_content: str, product_name: str = "") -> str:
    """
    Apply a prompt from a markdown file to the RCA content
    
    Args:
        prompt_file_path: Path to the prompt.md file
        rca_content: The RCA/bug content to analyze
        product_name: Optional product name for context
    
    Returns:
        LLM response as string
    """
    # Read the prompt file
    with open(prompt_file_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # Replace placeholders with actual content
    full_prompt = prompt_template.replace("{rca_content}", rca_content)
    full_prompt = full_prompt.replace("{extracted_text}", rca_content)
    full_prompt = full_prompt.replace("{product_name}", product_name)
    full_prompt = full_prompt.replace("{product}", product_name)
    
    # Get LLM and invoke
    llm = get_llm()
    result = llm.invoke(full_prompt)
    
    return result.content if hasattr(result, 'content') else str(result)
