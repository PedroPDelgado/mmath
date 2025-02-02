import streamlit as st
import random
import time
import datetime
from notion_client import Client

# Load Notion API credentials from Streamlit secrets
NOTION_TOKEN = st.secrets["notion_token"]
DATABASE_ID = st.secrets["notion_database_id"]
notion = Client(auth=NOTION_TOKEN)

# Streamlit page config
st.set_page_config(page_title="Mental Math Trainer", layout="centered")
st.title("🧮 Mental Math Trainer")

# Initialize session state variables
if "operation" not in st.session_state:
    st.session_state.operation = "add"
if "num_questions" not in st.session_state:
    st.session_state.num_questions = 5
if "digits" not in st.session_state:
    st.session_state.digits = (1, 1)
if "questions" not in st.session_state:
    st.session_state.questions = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = []
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "elapsed_time" not in st.session_state:
    st.session_state.elapsed_time = 0
if "completed" not in st.session_state:
    st.session_state.completed = False
if "running" not in st.session_state:
    st.session_state.running = False

# Sidebar menu for settings
st.sidebar.header("Settings")
new_operation = st.sidebar.selectbox("Operation", ["add", "sub", "mul"], index=["add", "sub", "mul"].index(st.session_state.operation))
new_digits = (
    st.sidebar.slider("Digits for first operand", 1, 3, st.session_state.digits[0]),
    st.sidebar.slider("Digits for second operand", 1, 3, st.session_state.digits[1])
)
new_num_questions = st.sidebar.selectbox("Number of questions", [5, 15, 25, 50], index=[5, 15, 25, 50].index(st.session_state.num_questions))

# If settings change, regenerate questions
if (new_operation != st.session_state.operation or new_digits != st.session_state.digits or new_num_questions != st.session_state.num_questions):
    st.session_state.operation = new_operation
    st.session_state.digits = new_digits
    st.session_state.num_questions = new_num_questions
    st.session_state.questions = []
    st.session_state.user_answers = []
    st.session_state.elapsed_time = 0
    st.session_state.start_time = None
    st.session_state.running = False
    st.session_state.completed = False

# Timer display and update
timer_placeholder = st.sidebar.empty()
if st.session_state.running:
    st.session_state.elapsed_time = time.time() - st.session_state.start_time
    timer_placeholder.write(f"Elapsed Time: {st.session_state.elapsed_time:.2f} sec")

# Start/Pause/Resume button in sidebar
button_text = "Start" if not st.session_state.running and st.session_state.start_time is None else ("Resume" if not st.session_state.running else "Pause")
if st.sidebar.button(button_text):
    if st.session_state.running:
        st.session_state.running = False  # Pause
        st.session_state.elapsed_time = time.time() - st.session_state.start_time
    else:
        st.session_state.running = True  # Resume
        if st.session_state.start_time is None:
            st.session_state.start_time = time.time()  # Start timing
        else:
            st.session_state.start_time = time.time() - st.session_state.elapsed_time
    st.rerun()

# Generate new questions if not set
if not st.session_state.questions:
    for _ in range(st.session_state.num_questions):
        a = random.randint(10**(st.session_state.digits[0] - 1), 10**st.session_state.digits[0] - 1)
        b = random.randint(10**(st.session_state.digits[1] - 1), 10**st.session_state.digits[1] - 1)
        if st.session_state.operation == "add":
            correct = a + b
            op_symbol = "+"
        elif st.session_state.operation == "sub":
            correct = a - b
            op_symbol = "-"
        else:
            correct = a * b
            op_symbol = "×"
        st.session_state.questions.append((a, b, correct, op_symbol))
    st.session_state.user_answers = [None] * st.session_state.num_questions

# Display questions
st.write("### Solve these:")
for i, (a, b, correct, op_symbol) in enumerate(st.session_state.questions):
    user_answer = st.number_input(f"{a} {op_symbol} {b} =",
                                  value=st.session_state.user_answers[i] if st.session_state.user_answers[i] is not None else None,
                                  step=1,
                                  key=f"q{i}",
                                  disabled=not st.session_state.running)
    st.session_state.user_answers[i] = user_answer

# Submit answers
if st.button("Submit Answers") and not st.session_state.completed:
    st.session_state.completed = True
    total_time = round(st.session_state.elapsed_time, 2)
    correct_answers = sum(
        1 for i, (_, _, correct, _) in enumerate(st.session_state.questions)
        if st.session_state.user_answers[i] == correct
    )
    accuracy = round((correct_answers / st.session_state.num_questions) * 100, 2)
    st.success(f"Completed in {total_time} seconds! ✅ {correct_answers}/{st.session_state.num_questions} correct ({accuracy}%).")

    # Log results to Notion
    notion_data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Title": {"title": [
                {
                    "text": {
                        "content": ""  # Using today's date as text
                    }
                }
            ]},
            "Date": {"date": {"start": str(datetime.date.today())}},
            "Operation": {"rich_text": [{"text": {"content": st.session_state.operation}}]},
            "Time Taken": {"number": total_time},
            "Correct Answers": {"number": correct_answers},
            "Total Questions": {"number": st.session_state.num_questions},
            "Accuracy": {"number": accuracy}
        }
    }
    try:
        notion.pages.create(**notion_data)
        st.success("Results saved to Notion! 🎉")
    except Exception as e:
        st.error(f"Failed to save to Notion: {e}")

# Restart button
if st.button("Try Again"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.running = False
    st.session_state.start_time = None
    st.session_state.elapsed_time = 0
    st.session_state.completed = False
    st.rerun()
