
import os
import json
import git
from typing_extensions import Annotated
from langchain.tools import tool, ToolException
from langgraph.prebuilt import InjectedState

@tool
def json_writer(json_string: str, filename: str, state: Annotated[dict, InjectedState]) -> str:
    """Writes a JSON string to a JSON file, given the filename.
    input args:
        json_string: str : The JSON string to write to the file (full markdown)
        filename: str : The name of the file to write the JSON string to (e.g., pid0011_clinical_summary.json)
        state: dict : The agent state containing metadata such as output_base_path (injected automatically by langgraph - do not fabricate)
    """
    try:
        output_base_path = get_metadata_from_state(state, "output_base_path")
        filepath = os.path.join(output_base_path, filename)
        
        # Fix incomplete JSON by counting and completing braces
        json_string = json_string.strip()
        
        # Count opening and closing braces
        open_braces = json_string.count('{')
        close_braces = json_string.count('}')
        missing_braces = open_braces - close_braces
        
        # Add missing closing braces
        if missing_braces > 0:
            json_string += '}' * missing_braces
        
        decoder = json.JSONDecoder()
        obj, idx = decoder.raw_decode(json_string)
        
        with open(filepath, 'w') as f:
            json.dump(obj, f, indent=4)
        return f"Data written to {filepath}"
    except json.JSONDecodeError as e:
        raise ToolException(f"json_writer error: Invalid JSON - {e}. String: {json_string[:500]}")
    except Exception as e:
        raise ToolException(f"json_writer error: {e}")

@tool
def text_reader(filename: str,state: Annotated[dict, InjectedState]) -> str:
    """Reads a text file and returns its content, given the filename."""
    try:
        input_base_path = get_metadata_from_state(state, "input_base_path")
        filepath = os.path.join(input_base_path, filename)
        with open(filepath, 'r') as file:
            content = file.read()
        return content
    except ToolException as e:
        raise ToolException(f"text_reader error: {e}")

@tool
def text_writer(content: str, filename: str, state: Annotated[dict, InjectedState]) -> str:
    """Writes text to a file.
    input args:
        content: str : The text content to write to the file (full markdown)
        filename: str : The name of the file to write the text content to (e.g., pid0011_clinical_notes_with_toc.md)
        state: dict : The agent state containing metadata such as output_base_path (injected automatically by langgraph - do not fabricate)
    """
    try:
        output_base_path = get_metadata_from_state(state, "output_base_path")
        filepath = os.path.join(output_base_path, filename)
        with open(filepath, 'w') as file:
            file.write(content)
        return f"Text written to {filepath}"
    except ToolException as e:
        raise ToolException(f"text_writer error: {e}")

@tool
def git_cloner(repo_url: str, clone_path: str) -> str:
    """Clones a Git repository to a specified path."""
    git.Repo.clone_from(repo_url, clone_path)
    return f"Repository cloned to {clone_path}"


def get_metadata_from_state(state: dict, key: str) -> dict:
    """Extracts metadata from the agent state messages."""
    metadata = {}
    for m in reversed(state["messages"]):
        if getattr(m, "additional_kwargs", None):
            if key in m.additional_kwargs:
                metadata = m.additional_kwargs
                return metadata
    

def add_line_numbers(text: str) -> str:
    """Adds line numbers to each line in the given text."""
    lines = text.split('\n')
    numbered_lines = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
    return '\n'.join(numbered_lines)


def load_patient_data(patient_id: int, base_path: str = ".", line_numbers: bool = True) -> dict:
    """Loads patient data from text files."""
    patient_id_str = f"pid{int(patient_id):04d}"
    note_fp = os.path.join(base_path, f"{patient_id_str}_note.txt")
    question_fp = os.path.join(base_path, f"{patient_id_str}_question.txt")
    answer_fp = os.path.join(base_path, f"{patient_id_str}_answer.txt")
    
    with open(note_fp, 'r') as f:
        note = f.read()
        
    if line_numbers:
        note = add_line_numbers(note)
        
    with open(question_fp, 'r') as f:
        question = f.read()
    
    with open(answer_fp, 'r') as f:
        answer = f.read()
    
    return {
        "patient_id": patient_id,
        "note": note,
        "question": question,
        "answer": answer
    }


def create_xml_document(data: dict, root_tag: str="documents") -> str:
    """Creates a simple XML document from a dictionary."""
    xml_content = f"<{root_tag}>\n"
    for key, value in data.items():
        xml_content += f"  <{key}>{value}</{key}>\n"
    xml_content += f"</{root_tag}>\n"
    return xml_content

