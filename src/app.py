
import os
import json
import time

import local_tools
import agents
import utils
from utils import ConfigLoader


AGENT_CONFIG_PATH = "/Users/ebadahmadzadeh/ms-code-projects/ethermed/langgraph_agent_app/src/agent_config.yaml"
PATIENT_DATA_BASE_PATH = "/Users/ebadahmadzadeh/ms-code-projects/ethermed/langgraph_agent_app/data/text_files"
OUTPUT_BASE_PATH = "/Users/ebadahmadzadeh/ms-code-projects/ethermed/langgraph_agent_app/outputs"
SKILL_PATH = "/Users/ebadahmadzadeh/ms-code-projects/ethermed/langgraph_agent_app/skills"


def run_skill(skill_name: str, patient_id_list: list[int]) -> None:
    """Runs the specified skill for the given patient ID."""
    assert skill_name in ["clinical_insights_skill", "clinical_judge_skill"], \
        f"Unsupported skill name: {skill_name}"
    agent_config = ConfigLoader(AGENT_CONFIG_PATH).dotdict
    agent = agents.prepare_agent(
        skill_name, SKILL_PATH, agent_config, data_xml=None)
    
    total_latency_s = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    for patient_id in patient_id_list:
        metadata = {"patient_id": patient_id, "output_base_path": OUTPUT_BASE_PATH}
        session_id = f"patient_{int(patient_id):04d}_{skill_name}_session"
        patient_data = local_tools.load_patient_data(
            patient_id, base_path=PATIENT_DATA_BASE_PATH, line_numbers=True)
        
        documents_dict, documents_xml = None, None
        if skill_name == "clinical_insights_skill":
            documents_dict = {
                "patient_id": patient_data["patient_id"],
                "notes": patient_data["note"],
                "questions": patient_data["question"],
            }
        else:
            treatment_plan_response = json.load(
                open(os.path.join(
                    OUTPUT_BASE_PATH,
                    f"pid{patient_id:04d}_treatment_recommendation.json")))
            summarization_response = json.load(
                open(os.path.join(
                    OUTPUT_BASE_PATH,
                    f"pid{patient_id:04d}_clinical_summary.json")))
            documents_dict = {
                "patient_id": patient_id,
                "notes": patient_data["note"],
                "treatment_plan_query": "Extract the treatment plan from the patient data.",
                "treatment_plan_response": treatment_plan_response.get("recommended_treatment", ""),
                "summarization_query": patient_data["question"],
                "summarization_ground_truth": patient_data["answer"],
                "summarization_response": summarization_response.get("summary", "")
            }
            
        documents_xml = local_tools.create_xml_document(
                documents_dict, root_tag="documents")
        p_start = time.perf_counter()
        token_usage = agents.run_agent(agent, session_id, stream_mode="values",
                                       user_query=documents_xml, metadata=metadata)

        # measure runtime and token usage:
        p_duration = round(time.perf_counter() - p_start, 2)
        total_latency_s += p_duration
        total_input_tokens += token_usage.input_tokens
        total_output_tokens += token_usage.output_tokens
        total_tokens += token_usage.total_tokens
        
        # save token usage per patient:
        token_usage_filepath = os.path.join(
            OUTPUT_BASE_PATH, f"pid{patient_id:04d}_{skill_name}_token_usage.json")
        token_usage.save(token_usage_filepath)
        # reset the token usage for the next patient:
        agent.token_usage.reset()

    # print overall stats:
    print(f"\n=== Overall Stats for skill: {skill_name} ===")
    print(f"Total Patients Processed: {len(patient_id_list)}")
    print(f"Total Latency (s): {total_latency_s:.2f}")
    print(f"Total Input Tokens: {total_input_tokens}")
    print(f"Total Output Tokens: {total_output_tokens}")
    print(f"Total Tokens: {total_tokens}")
    print(f"Average Latency per Patient (s): {total_latency_s / len(patient_id_list):.2f}")
    print(f"Average Input Tokens per Patient: {total_input_tokens / len(patient_id_list):.2f}")
    print(f"Average Output Tokens per Patient: {total_output_tokens / len(patient_id_list):.2f}")
    print(f"Average Tokens per Patient: {total_tokens / len(patient_id_list):.2f}")
    

if __name__ == "__main__":
    # run skills:
    # PID_LIST = [2, 5, 11, 13, 20, 36]
    PID_LIST = [11]
    run_skill("clinical_insights_skill", patient_id_list=PID_LIST)
    # run_skill("clinical_judge_skill", patient_id_list=PID_LIST)
