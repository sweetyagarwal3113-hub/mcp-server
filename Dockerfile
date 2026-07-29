# Use Microsoft Playwright official Python image with pre-installed browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy dependency requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser binary
RUN playwright install chromium

# Copy full application codebase
COPY . .

# Set Environment Variables for Production
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit Web Application
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
