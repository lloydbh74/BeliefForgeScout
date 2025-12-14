FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (none really needed for this stack, but good practice)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first to cache layer
COPY scout/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code to /app/scout so python path works
COPY scout/ /app/scout/

# Set Python path to include /app
ENV PYTHONPATH=/app

# Expose Streamlit port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "scout/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
