FROM python:3.9

WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Expose the port that Streamlit will run on
EXPOSE 8501

# Command to run your Streamlit app
CMD ["streamlit", "run", "main.py"]
