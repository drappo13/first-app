FROM python:3.9-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install streamlit, requests, requests-oauthlib, plotly, openai
RUN pip install -r requirements.txt

# Command to run on container start
CMD ["streamlit", "run", "streamlit_app.py"]
