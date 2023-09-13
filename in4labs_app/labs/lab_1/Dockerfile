# syntax=docker/dockerfile:1
FROM python:3.10-slim-bullseye
# Set the working directory to /lab
WORKDIR /lab
# Requirements are installed here to ensure they will be cached.
COPY requirements.txt /lab/requirements.txt
# Install any needed packages specified in requirements.txt
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt
# Copy the current directory contents into the container at /lab
COPY app_1 /lab/app_1
# Make port 8000 available outside this container
EXPOSE 8000
# Run lab when the container launches
CMD ["flask", "--app", "app_1", "run", "--host", "0.0.0.0", "--port", "8000"]