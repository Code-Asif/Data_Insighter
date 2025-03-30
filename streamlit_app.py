from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.services.account import Account
import base64
import textwrap
import plotly.io as pio
import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import pdfkit
import time
import os

# Configure Gemini AI
genai.configure(api_key="AIzaSyCFHAd_L0QwsFSDvhLOUpGgijlVGVP9JW0")

model = genai.GenerativeModel("gemini-2.0-flash")

PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

st.set_page_config(page_title="AI-Powered Business Analytics", layout="wide")

st.title("📊 Data Insighter")
st.write("Upload your business data to get interactive reports and AI-driven insights.")

# File Upload
uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        st.success("File uploaded successfully!")
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    df.dropna(inplace=True)  # Remove null values

    st.subheader("Select Columns to Keep")
    selected_columns = st.multiselect("Choose columns:", df.columns.tolist(), default=df.columns.tolist())

    if selected_columns:
        df = df[selected_columns]

    st.write("### Preview of Processed Data")
    st.dataframe(df.head())

    column_types = {col: str(df[col].dtype) for col in df.columns}

    st.write("🔍 *Analyzing Data...* Please wait while AI generates insights.")
    time.sleep(2)

    # AI decides suitable visualization types
    prompt = f"""Given these columns and their data types:
    {column_types}
    Suggest 5 suitable visualization types (Pie, Bar, Line, Scatter, Histogram, or Geographic if applicable).
    Only return the chart names as a comma-separated list."""

    gemini_response = model.generate_content(prompt)

    if hasattr(gemini_response, "text"):
        viz_types = [v.strip().lower() for v in gemini_response.text.split(",") if v.strip().lower() in ["pie", "bar", "line", "scatter", "histogram"]]
        if len(viz_types) < 5:
            viz_types = ["bar", "line", "pie", "scatter", "histogram"][:5]  # Default fallback
    else:
        st.error("Error: AI did not return a valid response.")
        st.stop()

    st.write(f"*AI Selected Visualizations:* {', '.join(viz_types)}")

    charts = []
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

    # AI-Generated Business Summary
    summary_prompt = f"Given this dataset with columns: {', '.join(df.columns)}, provide a short summary of insights, trends, and possible business improvements."
    summary_response = model.generate_content(summary_prompt)

    summary_text = summary_response.text if hasattr(summary_response, "text") else "No insights generated."
    st.write(f"*Business Insights:* {summary_text}")

    # Arrange Visualizations in a Grid
    st.markdown("---")
    st.subheader("📈 Data Visualizations (5 Worksheets)")

    cols = st.columns(3)

    for i, fig in enumerate(charts[:5]):  
        with cols[i % 3]:  
            st.plotly_chart(fig, use_container_width=True, key=f"worksheet_{i}")

    if st.button("📥 Download Report as PDF"):
        st.write("🔄 Generating Report... Please wait.")

        # Save Charts as Images
        chart_images = []
        for i, fig in enumerate(charts):
            chart_path = f"chart_{i}.png"
            pio.write_image(fig, chart_path)  
            chart_images.append(chart_path)

        summary_title = "Key Insights from Your Business Data"

        wrapped_text = textwrap.wrap(summary_text, width=120)[:10]
        bullet_points = "".join(f"<li>{line.strip()}</li>" for line in wrapped_text if line.strip())

        summary_html = f"""
        <h1 style="text-align:center; color:#2C3E50;"> Data Insighter</h1>
        <h2 style="color:#1F618D;"> {summary_title}</h2>
        <ul style="font-size:16px; line-height:1.6; color:#283747;">
            {bullet_points}
        </ul>
        <hr>
        <h2 style="color:#1F618D;"> Data Visualizations</h2>
        """

        for img_path in chart_images:
            with open(img_path, "rb") as img_file:
                base64_img = base64.b64encode(img_file.read()).decode()
            summary_html += f'<img src="data:image/png;base64,{base64_img}" style="width:100%; margin-bottom:20px;">'

        pdf_path = "Business_Report.pdf"
        pdfkit.from_string(summary_html, pdf_path, configuration=PDFKIT_CONFIG)

        with open(pdf_path, "rb") as file:
            st.download_button("📥 Download Report", file, file_name="Business_Report.pdf", mime="application/pdf")

    # AI Chatbot Section
    st.markdown("---")
    st.subheader("🤖 AI Chatbot for Data Queries")

    chat_history = st.session_state.get("chat_history", [])

    def chatbot_response(user_query):
        """Fetch response from Gemini AI, limited to uploaded data"""
        query_prompt = f"Analyze this dataset with columns: {', '.join(df.columns)} and answer briefly: {user_query}"
        chat_response = model.generate_content(query_prompt)
        return chat_response.text[:200] if hasattr(chat_response, "text") else "No response."

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


