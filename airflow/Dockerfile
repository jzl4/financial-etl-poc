# Seems that 3.0.4 is the most recent stable version
FROM apache/airflow:3.0.4

# Get user's ID on Linux OS
ARG AIRFLOW_UID=50000

# Switches active user inside of the container to root / admin
USER root

# Create a user group named "airflow" and assign it the group ID 1000
# Create a new user named "airflow" with user ID 1000 and make them a member of the group with ID 1000, and create a home directory for them
# Creates an "airflow" user inside of container whose UID and GID match my user's UID and GID on local EC2. Solves file permission issues
RUN groupadd --gid ${AIRFLOW_UID} airflow && \
    useradd --uid ${AIRFLOW_UID} --gid ${AIRFLOW_UID} -m airflow

# Copy requirements and install them
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Switch back to airflow user
USER airflow