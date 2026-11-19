FROM python:3.12-slim

WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY section1.py .

CMD ["streamlit", "run", "section1.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
