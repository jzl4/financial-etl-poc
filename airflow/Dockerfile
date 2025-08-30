# Most recent LTS version is 2.9.2
FROM apache/airflow:2.9.2

# Since we've sent the user ID to 1000 (which is the same as username in Linux) in credentials.env, that will flow into docker-compose.yaml as AIRFLOW_UID, and then flow into this Dockerfile
ARG AIRFLOW_UID 

# Switch to root to: modify user accounts, change file ownership, and install system packages
USER root

# Fix ownership issues before modifying the user
# First, change ownership of airflow's home directory and related files
RUN chown -R ${AIRFLOW_UID}:0 /home/airflow && \
    chown -R ${AIRFLOW_UID}:0 /opt/airflow

# Now modify the airflow user's UID to match the host
RUN usermod --uid ${AIRFLOW_UID} airflow

# Copy requirements and install them
COPY requirements.txt /requirements.txt

# Change ownership of the requirements file to the airflow user
RUN chown airflow:root /requirements.txt

# Switch back to airflow user BEFORE installing packages
USER airflow

# Install packages as the airflow user
RUN pip install --no-cache-dir -r /requirements.txt