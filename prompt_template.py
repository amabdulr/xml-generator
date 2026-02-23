from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from utils import get_llm

# Load the .env file
load_dotenv()

product_name = "Cisco SDWAN"
question = "what is the latest version of cisco SD-WAN?"

if __name__ == "__main__":
    print("Hello Prompt Template!")

    product_question_prompt_template = """
        given a Cisco product name and a question from a user, return the answer.
        Use the context provided to answer the question
        Cisco product: {product_name}
        question: {question}
        product context: {product_context}
        answer:
        """

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    vectorstore = Chroma(
        collection_name="cisco_products",
        persist_directory="data/cisco_products",
        embedding_function=embeddings,
    )

    result = vectorstore.similarity_search_with_score(question, k=2)

    product_context = ""
    for doc in result:
        product_context += doc[0].page_content

    product_prompt_template = PromptTemplate(
        input_variables=["product_name", "question", "product_context"],
        template=product_question_prompt_template,
    )

    llm = get_llm()
    chain = product_prompt_template | llm

    res = chain.invoke(
        input={
            "product_name": product_name,
            "question": question,
            "product_context": product_context,
        }
    )

    print(res)


# gpt-4o-mini response
# The latest version of Cisco SD-WAN is not specified in the provided context. Please check the official Cisco website or documentation for the most up-to-date information on Cisco SD-WAN versions.

# gpt-35-turbo
# The latest version of Cisco SD-WAN is not provided in the given context.

# llama3.1
# Unfortunately, there is no information provided about the latest version of Cisco SD-WAN in the context. The list mentions software versions for other Cisco products (ASA, FTD, FMC, FXOS), but not for Cisco SD-WAN.\n\nHowever, based on my general knowledge, I can suggest that you might need to check the official Cisco website or documentation for the latest version of Cisco SD-WAN. If you provide me with more context or information about the product's lifecycle, I'll do my best to help!

# mistral 7B
# As of Sep 2024, I don't have specific version information for Cisco SD-WAN as it includes multiple components, not just a single software package. However, you can check the latest versions for each component in the following list:\n\n1. vManage - Centralized network management system (version may vary)\n2. vSmart - Control plane component that manages policies and distribution of data (version may vary)\n3. vBond - Orchestrator that authenticates and authorizes the SD-WAN components (version may vary)\n4. vEdge - Virtual edge routers (version may vary)\n\nYou can visit the Cisco Software Center or consult with your network administrator for the most recent versions of these specific components in your Cisco SD-WAN environment.
