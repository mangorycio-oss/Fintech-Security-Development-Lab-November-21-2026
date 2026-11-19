from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Fintech Security Lab", layout="wide")
page = st.navigation([
    st.Page(Path("section2.py"), title="인증과 결제", default=True, url_path="home"),
    st.Page(Path("section2.py"), title="인증과 결제", url_path="section2"),
], position="hidden")
page.run()
