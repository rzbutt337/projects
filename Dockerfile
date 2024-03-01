# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install ffmpeg for audio processing
# Update apt package lists, install ffmpeg, and clean up apt cache to keep the image size down
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable for Gunicorn to listen on all network interfaces
ENV PORT=8080

# Use Gunicorn to serve the application. Adjust the number of workers and threads as necessary.
# The shell form to ensure environment variable is correctly interpreted
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 main2:app
