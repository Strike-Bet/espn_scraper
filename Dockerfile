# Use the official Python 3.8 image as the base image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install the required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . /app/

# Specify the command to run your scraper script
CMD ["python3", "extract_boxscore.py"]