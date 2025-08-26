# Most recent LTS verison is 2.9.2
FROM apache/airflow:2.9.2

# Get user's ID on Linux OS
ARG AIRFLOW_UID=50000

# Switches active user inside of the container to root / admin
USER root

# Modify the existing airflow user to have the host's UID,
# but assign it to the root group (GID=0) as required by the image.
RUN usermod --uid ${AIRFLOW_UID} --gid 0 airflow

# Copy requirements and install them
COPY requirements.txt /requirements.txt

# Change ownership of the file to the airflow user
RUN chown airflow:airflow /requirements.txt

# Switch back to airflow user BEFORE installing packages
USER airflow

# Now, install packages as the airflow user
RUN pip install --no-cache-dir -r /requirements.txt