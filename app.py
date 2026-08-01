import streamlit as st

st.set_page_config(
    page_title="Second Brain",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Second Brain")
st.subheader("Your Offline AI Knowledge Assistant")

st.divider()

uploaded_file = st.file_uploader(
    "📄 Upload a PDF",
    type=["pdf"]
)

question = st.text_input(
    "💬 Ask a question"
)

if st.button("Ask AI"):
    if uploaded_file is None:
        st.warning("Please upload a PDF first.")
    elif question == "":
        st.warning("Please enter a question.")
    else:
        st.success("Everything is working! 🎉")
        st.write("PDF:", uploaded_file.name)
        st.write("Question:", question)