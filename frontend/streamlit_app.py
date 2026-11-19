import streamlit as st

st.set_page_config(page_title="Fintech Security Lab", layout="wide")
page = st.navigation([
    st.Page("section1.py", title="Section 1 · 시큐어 코딩", default=True),
    st.Page("section2.py", title="Section 2 · 인증과 결제"),
])
page.run()
