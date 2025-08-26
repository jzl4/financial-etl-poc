# Most recent LTS version is 2.9.2
FROM apache/airflow:2.9.2

# Get user's ID on Linux OS
ARG AIRFLOW_UID=50000

# Switch to root to perform system modifications
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