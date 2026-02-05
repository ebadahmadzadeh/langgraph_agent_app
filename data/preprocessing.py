
import os
import pandas as pd


# set pandas display options for better readability
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', 20)

csv_fp = "/Users/ebadahmadzadeh/ms-code-projects/ethermed/langgraph_agent_app/data/synthetic.csv"
output_text_base_path = "/Users/ebadahmadzadeh/ms-code-projects/ethermed/langgraph_agent_app/data/text_files"


def load_data(filepath: str, task_name: str = "Summarization", num_rows: int = None) -> pd.DataFrame:
    """Loads data from a CSV file and filters by task name."""
    df = pd.read_csv(filepath)
    filtered_df = df[df['task'] == task_name]
    if num_rows is not None:
        filtered_df = filtered_df.head(num_rows)
    return filtered_df


def show_head(dataframe: pd.DataFrame, num_rows: int = 5):
    """Displays the first few rows of the DataFrame."""
    print(dataframe.head(num_rows))
    
def show_note(dataframe: pd.DataFrame, row_index: int):
    """Displays the note column of a specific row."""
    if 0 <= row_index < len(dataframe):
        print(f"Note of row {row_index}: {dataframe.iloc[row_index]['note']}")
    else:
        print("Row index out of range.")


def show_note_length_stats(dataframe: pd.DataFrame):
    """Displays statistics about the lengths of notes in the DataFrame."""
    note_lengths = dataframe['note'].apply(len)
    print("Note Length Statistics:")
    print(f"Mean: {note_lengths.mean()}")
    print(f"Median: {note_lengths.median()}")
    print(f"Max: {note_lengths.max()}")
    print(f"Min: {note_lengths.min()}")


def save_row_as_text_files(dataframe: pd.DataFrame, base_path: str = "."):
    """Saves each row as 3 text files."""
    # create base path directory if it doesn't exist
    os.makedirs(base_path, exist_ok=True)
    for index, row in dataframe.iterrows():
        patient_id = row['patient_id']
        # note = row['note']
        note = row['note']
        question = row['question']
        answer = row['answer']
        
        patient_id = f"pid{int(patient_id):04d}"
        with open(f"{base_path}/{patient_id}_note.txt", "w") as f:
            f.write(note)

        with open(f"{base_path}/{patient_id}_question.txt", "w") as f:
            f.write(question)

        with open(f"{base_path}/{patient_id}_answer.txt", "w") as f:
            f.write(answer)


if __name__ == "__main__":
    df = load_data(csv_fp, task_name="Summarization", num_rows=10)
    # show_head(df, num_rows=5)
    # show_note(df, row_index=2)
    # show_note_length_stats(df)
    save_row_as_text_files(df ,base_path=output_text_base_path)
