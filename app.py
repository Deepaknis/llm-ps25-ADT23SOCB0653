
import streamlit as st
import pandas as pd
import json
import os
from datetime import date
from dotenv import load_dotenv
from google import genai

# Load API key
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Study Plan Generator",
    page_icon="📚",
    layout="wide"
)

# Initialize Gemini
api_key = os.getenv("GEMINI_API_KEY")

# Application heading
st.title("📚 AI Study Plan Generator")
st.write(
    "Generate your personalized exam preparation timetable "
    "using Artificial Intelligence."
)

st.divider()

# Sidebar
st.sidebar.header("⚙️ Study Settings")

start_date = st.sidebar.date_input(
    "Preparation Start Date",
    value=date.today()
)

daily_hours = st.sidebar.slider(
    "Available Study Hours Per Day",
    min_value=1,
    max_value=12,
    value=5
)

st.sidebar.info(
    "Enter your subjects, exam dates and syllabus topics "
    "to generate your timetable."
)

# Subject and syllabus input
st.subheader("1. Enter Your Subjects and Syllabus")

st.write(
    "Enter one subject per line using this format:"
)

st.code(
    "Subject Name | YYYY-MM-DD | Topic 1, Topic 2, Topic 3"
)

syllabus = st.text_area(
    "Subjects and Syllabus",
    value=(
        "Natural Language Processing | 2026-11-30 | "
        "Introduction, WordNet, Parsing, WSD\n"
        "Deep Learning | 2026-12-02 | "
        "ANN, CNN, RNN, LSTM\n"
        "Big Data Analytics | 2026-12-04 | "
        "Hadoop, HDFS, MapReduce, Hive"
    ),
    height=160,
    placeholder="Enter your subjects here..."
)

# Generate timetable
if st.button("✨ Generate My Study Plan", type="primary"):

    if not api_key:
        st.error(
            "Gemini API key not found. Please add it to your .env file."
        )

    elif not syllabus.strip():
        st.warning("Please enter your subjects and syllabus.")

    else:
        try:
            # Read subject information
            subjects = []

            for line in syllabus.strip().splitlines():

                parts = line.split("|")

                if len(parts) != 3:
                    raise ValueError(
                        "Each line must contain Subject | Exam Date | Topics."
                    )

                subject = parts[0].strip()
                exam_date = date.fromisoformat(parts[1].strip())
                topics = [
                    topic.strip()
                    for topic in parts[2].split(",")
                    if topic.strip()
                ]

                if not subject or not topics:
                    raise ValueError(
                        "Every subject must have a name and at least one topic."
                    )

                if exam_date <= start_date:
                    raise ValueError(
                        f"The exam date for {subject} must be after "
                        "the preparation start date."
                    )

                subjects.append({
                    "subject": subject,
                    "exam_date": str(exam_date),
                    "topics": topics
                })

            # Create AI prompt
            prompt = f"""
You are an expert AI study planner.

Create a realistic day-wise study timetable for a student.

STUDENT INFORMATION:
Preparation start date: {start_date}
Available study hours per day: {daily_hours}

SUBJECTS AND SYLLABUS:
{json.dumps(subjects, indent=2)}

INSTRUCTIONS:
1. Schedule all syllabus topics before their respective exam dates.
2. Prioritize subjects according to their exam dates.
3. Divide difficult topics into manageable study sessions.
4. Distribute the available study hours fairly.
5. Never exceed {daily_hours} total study hours on any day.
6. Include revision sessions and practice tests.
7. Schedule final revision before each subject's exam.
8. Do not schedule a subject after its exam date.
9. Use dates in YYYY-MM-DD format.
10. Include realistic start and end times.
11. Keep the total daily hours within the student's limit.
12. Do not invent additional syllabus topics.

Return ONLY valid JSON in this format:

{{
  "schedule": [
    {{
      "date": "YYYY-MM-DD",
      "subject": "Subject Name",
      "topic": "Topic Name",
      "activity": "Study / Revision / Practice Test",
      "start_time": "09:00 AM",
      "end_time": "10:00 AM",
      "hours": 1
    }}
  ]
}}

Make sure the timetable covers every provided syllabus topic.
"""

            # Call Gemini API
            with st.spinner(
                "AI is analyzing your syllabus and preparing your timetable..."
            ):

                client = genai.Client(api_key=api_key)

                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json"
                    }
                )

                result = json.loads(response.text)

                schedule = result.get("schedule", [])

                if not schedule:
                    raise ValueError(
                        "AI did not return any timetable entries."
                    )

                # Convert to DataFrame
                df = pd.DataFrame(schedule)

                required_columns = [
                    "date",
                    "subject",
                    "topic",
                    "activity",
                    "start_time",
                    "end_time",
                    "hours"
                ]

                for column in required_columns:
                    if column not in df.columns:
                        raise ValueError(
                            f"Missing required field: {column}"
                        )

                # Validate generated dates and hours
                df["date"] = pd.to_datetime(
                    df["date"],
                    format="%Y-%m-%d",
                    errors="raise"
                )

                df["hours"] = pd.to_numeric(
                    df["hours"],
                    errors="raise"
                )

                if (
                    df["hours"].isna().any()
                    or (df["hours"] <= 0).any()
                    or (df["hours"] > daily_hours).any()
                ):
                    raise ValueError(
                        "AI generated invalid study hours."
                    )

                df = df.sort_values(
                    by=["date", "start_time"]
                ).reset_index(drop=True)

                daily_totals = df.groupby("date")["hours"].sum()

                if (daily_totals > daily_hours).any():
                    raise ValueError(
                        "The generated timetable exceeds your daily "
                        "study-hour limit. Please try again."
                    )

                # Display results
                st.session_state["study_plan"] = df

                st.success(
                    "Your AI-generated study timetable is ready!"
                )

        except Exception as e:
            st.error(f"Error: {e}")

# Display generated timetable
if "study_plan" in st.session_state:

    df = st.session_state["study_plan"]

    st.divider()
    st.subheader("2. Your Generated Study Timetable")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Study Sessions",
        len(df)
    )

    col2.metric(
        "Total Study Hours",
        round(df["hours"].sum(), 1)
    )

    col3.metric(
        "Subjects",
        df["subject"].nunique()
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # Daily summary
    st.subheader("3. Daily Study Hours")

    daily_summary = (
        df.groupby("date")["hours"]
        .sum()
        .reset_index()
    )

    daily_summary["date"] = (
        daily_summary["date"].dt.strftime("%d-%m-%Y")
    )

    st.bar_chart(
        daily_summary.set_index("date")
    )

    # CSV download
    st.subheader("4. Download Your Study Plan")

    csv_data = df.copy()
    csv_data["date"] = csv_data["date"].dt.strftime("%Y-%m-%d")

    csv_file = csv_data.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download Study Plan as CSV",
        data=csv_file,
        file_name="AI_Study_Plan.csv",
        mime="text/csv"
    )

    st.success(
        "You can now use your downloaded timetable "
        "for daily exam preparation!"
    )
