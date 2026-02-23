import json
from typing import List
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from utils import get_llm


@tool
def extract_bugs_from_text(input: str) -> List[str]:
    """
    :return: list of bugs found in the input text
    """
    llm = get_llm()
    extract_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a text extraction tool that extracts bugs from text. "
                "Bugs always start with CSC, then 2 letters, then 5 numbers. "
                "Here are some examples: CSCab12345, CSCxx11111.\n"
                "if you can't find any bugs, return an empty list.\n"
                "You should return a list of bugs found in the text. here are some examples:\n"
                'Input: "CSCab12345", "CSCxx11111"\n\n'
                'Output: ["CSCab12345", "CSCxx11111"]\n'
                "Input: the bug id is CSCwz56373\n\n"
                'Output: ["CSCwz56373"]\n'
                "Input: no bugs here, or invalid bug id 12345\n\n"
                "Output: []",
            ),
            ("human", "Input: {input}\n\n" "Output:"),
        ]
    )

    bug_list_chain = extract_prompt | llm | StrOutputParser()
    bug_list = bug_list_chain.invoke({"input": input})
    return json.loads(bug_list)


if __name__ == "__main__":
    print("Hello structured output!")
    input_text = "The bug id is CSCwz56373 and CSCab12345. The bug id is invalid 12345."
    bugs = extract_bugs_from_text(input_text)
    print(f"Extracted bugs: {bugs}")
