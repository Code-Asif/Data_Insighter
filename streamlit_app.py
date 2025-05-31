import base64
import textwrap
import plotly.io as pio
import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import time
import os
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# Load environment variable
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# Streamlit UI setup
st.set_page_config(page_title="AI-Powered Business Analytics", layout="wide")
st.title("📊 Data Insighter")
st.write("Upload your business data to get interactive reports and AI-driven insights.")

uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        st.success("File uploaded successfully!")
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    df.dropna(inplace=True)

    st.subheader("Select Columns to Keep")
    selected_columns = st.multiselect("Choose columns:", df.columns.tolist(), default=df.columns.tolist())
    if selected_columns:
        df = df[selected_columns]

    st.write("### Preview of Processed Data")
    st.dataframe(df.head())

    column_types = {col: str(df[col].dtype) for col in df.columns}

    st.write("🔍 *Analyzing Data...* Please wait while AI generates insights.")
    time.sleep(2)

    prompt = f"""Given these columns and their data types:
    {column_types}
    Suggest 5 suitable visualization types (Pie, Bar, Line, Scatter, Histogram, or Geographic if applicable).
    Only return the chart names as a comma-separated list."""

    gemini_response = model.generate_content(prompt)

    if hasattr(gemini_response, "text"):
        viz_types = [v.strip().lower() for v in gemini_response.text.split(",") if v.strip().lower() in ["pie", "bar", "line", "scatter", "histogram"]]
        if len(viz_types) < 5:
            viz_types = ["bar", "line", "pie", "scatter", "histogram"][:5]
    else:
        st.error("Error: AI did not return a valid response.")
        st.stop()

    st.write(f"*AI Selected Visualizations:* {', '.join(viz_types)}")

    charts = []
    chart_images = []

    for viz in viz_types:
        st.subheader(f"📌 {viz.capitalize()} Chart")
        fig = None
        if viz == "pie":
            column = st.selectbox("Select column for Pie Chart", df.columns, key="pie")
            fig = px.pie(df, names=column, title=f"Distribution of {column}")
        elif viz == "bar":
            x_col = st.selectbox("X-axis for Bar Chart", df.columns, key="bar_x")
            y_col = st.selectbox("Y-axis for Bar Chart", df.columns, key="bar_y")
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        elif viz == "line":
            x_col = st.selectbox("X-axis for Line Chart", df.columns, key="line_x")
            y_col = st.selectbox("Y-axis for Line Chart", df.columns, key="line_y")
            fig = px.line(df, x=x_col, y=y_col, title=f"Trend of {y_col} over {x_col}")
        elif viz == "scatter":
            x_col = st.selectbox("X-axis for Scatter Plot", df.columns, key="scatter_x")
            y_col = st.selectbox("Y-axis for Scatter Plot", df.columns, key="scatter_y")
            fig = px.scatter(df, x=x_col, y=y_col, title=f"Scatter Plot of {y_col} vs {x_col}")
        elif viz == "histogram":
            column = st.selectbox("Select column for Histogram", df.columns, key="hist")
            fig = px.histogram(df, x=column, title=f"Distribution of {column}")

        if fig:
            charts.append(fig)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📝 AI-Generated Business Insights")
    st.write("Analyzing data for key takeaways...")

    summary_prompt = f"Given this dataset with columns: {', '.join(df.columns)}, provide a summary of insights, trends, and possible business improvements."
    summary_response = model.generate_content(summary_prompt)

    if hasattr(summary_response, "text"):
        summary_text = summary_response.text
        st.write(f"*Business Insights:* {summary_text}")
    else:
        st.error("Error: AI did not return a valid summary.")
        st.stop()

    # Grid layout for charts
    st.markdown("---")
    st.subheader("📈 Data Visualizations (3×2 Grid)")
    cols = st.columns(3)
    for i, fig in enumerate(charts[:6]):
        with cols[i % 3]:
            st.plotly_chart(fig, use_container_width=True, key=f"worksheet_{i}")

    if st.button("📥 Download Report as PDF"):
        st.write("🔄 Generating PDF Report... Please wait.")

        # Save images with Plotly + Kaleido
        img_paths = []
        for i, fig in enumerate(charts[:5]):
            img_path = f"chart_{i}.png"
            pio.write_image(fig, img_path)
            img_paths.append(img_path)

        # Generate PDF with ReportLab
        pdf_file = "Business_Report.pdf"
        doc = SimpleDocTemplate(pdf_file, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [Paragraph("Data Insighter Report", styles["Title"]),
                 Spacer(1, 12),
                 Paragraph("Key Business Insights", styles["Heading2"])]

        for line in textwrap.wrap(summary_text, 100)[:10]:
            story.append(Paragraph(f"• {line}", styles["BodyText"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Charts", styles["Heading2"]))
        for img_path in img_paths:
            story.append(Spacer(1, 12))
            story.append(RLImage(img_path, width=450, height=300))

        doc.build(story)

        with open(pdf_file, "rb") as file:
            st.download_button("📥 Download PDF", file, file_name="Business_Report.pdf", mime="application/pdf")

    st.markdown("---")
    st.subheader("🤖 AI Chatbot for Data Queries")

    chat_history = st.session_state.get("chat_history", [])

    def chatbot_response(user_query):
        query_prompt = f"Analyze the uploaded dataset and answer: {user_query}"
        chat_response = model.generate_content(query_prompt)
        return chat_response.text if hasattr(chat_response, "text") else "I'm sorry, I couldn't process that."

    with st.expander("💬 Open AI Chatbot"):
        st.write("Ask questions about your uploaded data.")
        user_query = st.text_input("Enter your query:")

        if st.button("Ask AI"):
            if user_query:
                response = chatbot_response(user_query)
                chat_history.append({"query": user_query, "response": response})
                st.session_state.chat_history = chat_history

        if chat_history:
            for chat in reversed(chat_history):
                st.write(f"**You:** {chat['query']}")
                st.write(f"**AI:** {chat['response']}")

    if st.sidebar.button("💬 Open Chatbot"):
        st.sidebar.write("AI Chatbot is now active!")
        user_query_sidebar = st.sidebar.text_input("Ask AI:")
        if st.sidebar.button("Submit"):
            if user_query_sidebar:
                response_sidebar = chatbot_response(user_query_sidebar)
                st.sidebar.write(f"**AI:** {response_sidebar}")
