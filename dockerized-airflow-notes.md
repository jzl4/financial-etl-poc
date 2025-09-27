


- This assumes that you already have an existing AWS RDS database

###  Project Structure
- financial-etl-poc/ (git repo, main folder)
  - .venv
  - airflow/
    - config/
    - dags/
    - logs/
    - plugins/
    - docker-compose.yaml
    - Dockerfile
    - requirements.txt
  - fastapi-rolling-correlation
  - credentials.env
  - .gitignore

### docker-compose.yaml:
```
# Define a base configuration to avoid repetition
x-airflow-base: &airflow-base
  build:
    context: .
    dockerfile: Dockerfile
    args:
      # Since we've sent the user ID to 1000 (which is the same as username in Linux) in credentials.env, that will flow into docker-compose.yaml as AIRFLOW_UID as 1000 as well
      - AIRFLOW_UID=${AIRFLOW_UID}
  # user: "${AIRFLOW_UID:-1000}:0"   # run as your host UID, group root
  # Use the .env with RDS credentials in base folder: financial-etl-poc/.env
  env_file:
    - ../credentials.env
  environment:
    # Construct the database connection string from your .env variables
    - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${rds_username}:${rds_password}@${rds_host}:${rds_port}/${rds_dbname}
    # Set other core Airflow configurations
    - AIRFLOW__CORE__EXECUTOR=LocalExecutor
    - AIRFLOW__CORE__LOAD_EXAMPLES=false
    - AIRFLOW__CORE__FERNET_KEY=${FERNET_KEY}
    - AIRFLOW__WEBSERVER__SECRET_KEY=${WEBSERVER_SECRET_KEY:-your-super-secret-key-change-me} # Add a default secret key
  volumes:
    - ./config:/opt/airflow/config
    - ./dags:/opt/airflow/dags
    - ./logs:/opt/airflow/logs
    - ./plugins:/opt/airflow/plugins

services:

  # The service that initializes the Airflow database and creates the first user
  airflow-init:
    <<: *airflow-base
    container_name: airflow_init
    entrypoint: /bin/bash
    command:
      - -c
      - |
        # Initialize the database
        airflow db migrate
        # Create the admin user if they don't exist
        airflow users create \
          --username ${AIRFLOW_USERNAME} \
          --password ${AIRFLOW_PASSWORD} \
          --firstname Joe \
          --lastname Lu \
          --role Admin \
          --email Joe.Zhou.Lu@gmail.com || true

  # The Airflow webserver service
  airflow-webserver:
    <<: *airflow-base
    container_name: airflow_webserver
    restart: always
    command: airflow webserver
    ports:
      - "8080:8080"
    depends_on:
      # This ensures the webserver only starts after the database is initialized
      airflow-init:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # The Airflow scheduler service
  airflow-scheduler:
    <<: *airflow-base
    container_name: airflow_scheduler
    restart: always
    command: airflow scheduler
    depends_on:
      # This ensures the scheduler only starts after the database is initialized
      airflow-init:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD-SHELL", "airflow jobs check --job-type SchedulerJob --hostname \"$${HOSTNAME}\""]
      interval: 30s
      timeout: 10s
      retries: 3
```

- (To do: Explain every section of this)

### Dockerfile:
```
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
```

Explanation of this file:
```
FROM apache/airflow:2.9.2
```
- We start with the official Apache Airflow image version 2.9.2
- This version includes critical bug fixes from prior versions, including: scheduler memory leaks that occurred in 2.9.1, DAG parsing race conditions, UI performance issues with large DAGs, etc.
- Later versions such as 2.10.0+ introduce several breaking changes, including: changed default postgres provider behavior, deprecated several operators, changed default config values, etc.
- In a nutshell, many major companies are running 2.9.2 in production, given: stability proven at scale, community support is extensive, stack overflow has many 2.9.2-specific answers, and github issues are well-documented
```
ARG AIRFLOW_UID 
```
- We've set AIRFLOW_UID=1000 in credentials.env
- docker-compose.yaml pulls this parameter from credentials.env and assigns to AIRFLOW_UID
  ```
    # docker-compose.yaml
      args:
        - AIRFLOW_UID=${AIRFLOW_UID}
    env_file:
      - ../credentials.env
  ```
- That gets passed to the Dockerfile, so ultimately, the Dockerfile inherits the UID of 1000 from the credentials.env
  ```
    # docker-compose.yaml
  dockerfile: Dockerfile
  ```

```
USER root
```
- The base Airflow runs as the airflow user by default, but we need administrative privileges to: modify user accounts (usermod), change file ownership (chown), install system packages if needed

```
RUN chown -R ${AIRFLOW_UID}:0 /home/airflow && \
    chown -R ${AIRFLOW_UID}:0 /opt/airflow
```
- The airflow user in the base image has a specific UID (let's say 50000). All files in /home/airflow and /opt/airflow are owned by this UID.
- Your Goal: Change the airflow user's UID to match your host system (1000 in your case)
- The Issue: When usermod tries to change the UID (later on, in next line), it also tries to update file ownership, but it fails because it can't access/modify certain files
- The Solution: We manually change ownership BEFORE running usermod, because only root can modify user accounts (change UID), change file ownership, or install system packages.
- This code snippet says: "Give ownership to UID 1000, group 0 (root group), -R means recursive (all subdirectories and files), and apply this to /home/airflow (user's home directory) and /opt/airflow (where Airflow is installed)"
- We have to change the ownership of existing files BEFORE modifying the user, because currently, Airflow UID is 50000, these files are owned by UID 50000, so we have the power to change their ownership now.  Conversely if we change the user UID via "usermod..." to 1000 first, these files will become "orphaned" (owned by non-existent UID 50000), and then we cannot change ownership of these files because we are no longer the owner!
- Note: /home/airflow is separate from mounted volumes. This is airflow user's home directory inside of the container, and it contains .bashrc, .profile, and various config files

```
RUN usermod --uid ${AIRFLOW_UID} airflow
```
- Now that we've fixed the file ownership issues, usermod can successfully change the airflow user's UID from the original (50000) to your desired UID (1000).
- Why match UIDs? When you mount volumes from your host to the container, the host files are owned by your user ID (UID 1000), and container files are also owned by airflow user (now also UID 1000), so no permission conflicts
 

```
COPY requirements.txt /requirements.txt
RUN chown airflow:root /requirements.txt
```
- Copy requirements.txt file into the container as /requirements.txt
- Change ownership to "airflow user, root group" so that airflow user can read it.  Recall that airflow:root now refers to UID 1000 (not 50000)

```
USER airflow
RUN pip install --no-cache-dir -r /requirements.txt
```
-- Switch back to the airflow user for security best practices
-- Install Python packages as the non-root user from /requirements.txt (still UID 1000)
-- Argument --no-cache-dir saves space by not storing pip cache

In summary, this combination of steps in Dockerfile leads to:
1. airflow user has UID 50000
2. We manually change file ownership to UID 1000 first
3. usermod changes UID to 1000 (files already owned by 1000, so no conflicts)
4. Success!

### Docker containers and file directories
- Docker containers are isolated environments - Yes, like a lightweight virtual computer
- Containers have their own filesystem
- But, even without volume mounts, Docker containers already have a complete filesystem that physically exists on your EC2:
  - The container's filesystem is stored in the Docker's storage layers (usually in /var/lib/docker/)
  - Files written inside of the container go to a "writable layer" on your host's disk
  - And these files disappear when the container is removed
- Volume mounts are thus OPTIONAL.  They are used when you want to:
  - Persist data beyond the container's lifetime
  - Share files between the host and container
  - Develop code locally while running that code in a container
- Thus, volume mounts are required because:
  - DAGs need to be edited on EC2 and immediately refreshed/visible in the container
  - Logs need to persist even if the container restarts
  - Plugins/config need to be managed from outside of the container
- In the Dockerized Airflow setup, because you have a mount, which is a one-to-one link, between local folders to container folders, this prevents us from having to rebuild the Docker image every time that we modify the DAGs locally. This means that if I change a DAG locally on my EC2, that immediately becomes updated in the same exact way inside of the container
- If I update logs inside of the container with information on how my Airflow jobs performed, they would normally just get erased, so I can't read the logs on my local folders.  So, the mounted drives allow the logs to be written back to my local folders, so they can be persistent
- What happens if we don't have volume mounts for Airflow's Docker containers?
  - Every time we change anything in our DAGs in our local folders, we have to re-build the docker image using "docker compose build".  This would be time-consuming and bad practice
  - Logs created by Airflow running inside of the container cannot be sent back to my local machine, so I won't be able to read the logs after the container shuts off


### Scheduler and Webserver are actually separate containers!
- Each Airflow component runs in its own container, not all in one container.
```
# docker-compose.yaml typically has:
services:
  airflow-webserver:    # Container 1
    image: apache/airflow:2.x.x
    command: webserver
    volumes:
      - ./dags:/opt/airflow/dags  # Must mount DAGs
  
  airflow-scheduler:    # Container 2
    image: apache/airflow:2.x.x
    command: scheduler
    volumes:
      - ./dags:/opt/airflow/dags  # Must mount same DAGs
```

### When we mount drives/folders, how does Airflow's metabase get persisted?  Talk me through how airflow-init is related to this
- Typically, the external postgre container handles it
- Airflow-init is a one-time initialization container that:
  - Waits for the database to be ready
  - Runs database migrations (airflow db migrate)
  - Create admin user
  - Exits successfully
```
# Inside of docker-compose.yaml. The service that initializes the Airflow database and creates the first user
  airflow-init:
    <<: *airflow-base
    container_name: airflow_init
    entrypoint: /bin/bash
    command:
      - -c
      - |
        # Initialize the database
        airflow db migrate
        # Create the admin user if they don't exist
        airflow users create \
          --username ${AIRFLOW_USERNAME} \
          --password ${AIRFLOW_PASSWORD} \
          --firstname Joe \
          --lastname Lu \
          --role Admin \
          --email Joe.Zhou.Lu@gmail.com || true
    environment:
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    depends_on:
      - postgres
```
- airflow db migrate is idempotent (safe to run multiple times)
- User creation fails if user exists, but || true handles it
- Thus:
  - First run: User doesn't exist → Creates user → Success
  - Second run: User exists → Command fails → || true makes it succeed anyway
- The user account information is stored in the Airflow metadata database, not in containers or images:
  - ab_user table (Username, email, names)
  - ab_password table (Password hashes here)


### More detailed explanation of what is happening with file permissions, ownership, user IDs, etc.
- It's almost like we have two different computers trying to share files: local Linux machine (the host) and the Docker container (a mini Linux machine inside of your machine).  Each has their own users, which are identified by user IDs (UIDs)
- By default, without making these changes in Dockerfile, when you start up:
- On your host machine, your UID = 1000, the files that you create are owned by UID = 1000, so project folder /home/ubuntu/financial-etl-poc/ is owned by UID 1000
- Inside of the Airflow Docker container, there is an airflow user with UID = 50000 (different UID), so airflow files are owned by UID 50000 and airflow process runs as UID 50000
- When you mount volumes in docker-compose, you're essentially saying: "Hey Docker, let the container access my host folders directly":
```
volumes:
  - ./dags:/opt/airflow/dags
  - ./logs:/opt/airflow/logs
```
- But here is where issues arise:
  - Container side: /opt/airflow/dags (expects UID 50000) → Host side: ./dags (UID 1000)
  - Container side: /opt/airflow/logs (expects UID 50000) → Host side: ./logs (UID 1000)
- Result: The Airflow process (running as UID 50000) can't read/write your files (owned by UID 1000). Permission denied!
- What the Dockerfile fix actually does:
- Step 1: The Container Starts Building
  - Base airflow image: airflow user = UID 50000
  - All airflow files owned by UID 50000
- Step 2: We Get Your Host UID
  - ARG AIRFLOW_UID=1000  # This comes from your docker-compose
  - Your docker-compose passes in: "Hey, the host user is UID 1000"
- Step 3: We Fix Ownership BEFORE Changing the User
  ```
  # From Dockerfile
  RUN chown -R 1000:0 /home/airflow && \
    chown -R 1000:0 /opt/airflow
  ```
  - Takes ALL airflow files (originally owned by UID 50000)
  - Changes ownership to UID 1000 (your host user)
- Step 4: We Change the Airflow User's ID
  ```
  RUN usermod --uid 1000 airflow
  ```
  - Changes the airflow user from UID 50000 → UID 1000
  - Now airflow user has the SAME ID as your host user
- Step 5: Everything Lines Up! 
  - Host side: ubuntu (UID 1000) = container side: airflow (UID 1000)
  - Airflow can read/write your DAG files and write log files back to your host

### More on the file mapping issue
- Docker volumes create a bridge between local directories and container directories
- When writing inside the container, you're actually writing to the local filesystem
- The default EC2 user has UID 1000
- The Airflow default UID is 50000
- When we mount volumes:
  - The local directories retain their original ownership, typically 1000 on EC2
  - Inside the container, the mounted directories appear with the UID as they have the host (which is 1000)
  - The airflow process (running as 50000) tries to write to directories owned by UID 1000, which fails because UID 50000 doesn't have write permissions to UID 1000's directories
- Naturally, there are actually 2 ways to resolve this, then:
  - Option 1: Change Airflow UID to 1000
  - Option 2: Change local directory ownership to 50000
- Option 2 is less preferred because: the EC2 user (with UID 1000) loses direct ownership of these files, I'll need to use "sudo" to manage files locally, and it's really not intuitive to have an non-existent user (50000) own files on my local host


### How to check your identity in Linux CLI
How to check your UID on your local machine:
```
echo "Username: $(whoami), UID: $(id -u)"
```
This should return something like:
```
Username: ubuntu, UID: 1000
```

How to check your Airflow UID inside of Docker container
```
docker run --rm -it apache/airflow:2.9.2 bash -c "id airflow"
```
This should return something like:
```
uid=50000(airflow) gid=0(root) groups=0(root)
```




### How these pieces interact with each other
- The dockerfile is kind of for build time
- The docker-compose is kind of for run-time
- The new method of defining the user ID to be 1000 in the Dockerfile, as opposed to the docker-compose.yaml file, is much more stable (why is this?)

### Section explaining what each of these pieces mean
- Explain what is usually inside of config, dags, logs, plugins, etc.
- Explain what credientials.env contains.  Example: rds_username = blah blah, rds_password = blah blah
- The apache-airflow-providers-postgres package is the modern, official way to integrate Airflow with PostgreSQL.  It bundles everything that Airflow needs to talk to Postgres, including psycopg2, connection types for the UI, postreg-specific hooks, and operators to use in DAGs
- Connection Types (The UI Form): When you go to the Airflow UI to add a new connection to Postgres, the provider gives you a specific form with clearly labeled fields like "Host," "Schema," "Login," and "Port." Without the provider, Airflow wouldn't know to show you this specific, helpful form.
- Hooks (The Pre-Wired Adapter): A Hook is a pre-built Python class that handles all the boilerplate code for connecting to a database and running commands.  Instead of you writing psycopg2.connect(...), handling credentials, creating a cursor, and managing transactions in every task, you can just import PostgresHook and say pg_hook.run("SELECT * FROM my_table;"). It handles the messy connection details for you.
- Operators (The Remote Control Button): An Operator is a pre-built Airflow task. The PostgresOperator, for example, is a single button you can put in your DAG that is pre-programmed to do one thing: execute a SQL statement. You just tell it which SQL file to run, and it uses a PostgresHook under the hood to get the job done.

### Walkthrough of requirements.txt file
- A user ID is like a "social security number" for a user on a Linux-based system. The administrator (root) has a UID of 0, and typically the first "regular" (non-root) user is given UID of 1000
- However, typically, the default UID for Airflow process is 50000, which is differ from the UID of 1000
- This causes issues later on, when the Airflow process from inside of Docker container (with UID 50000) tries to write outside, via volume mounts, to local folders on EC2 with owner ID 1000; this will result in a "permission denied" error, for example, when writing to airflow/logs/ folder
- We resolve this in the Dockerfile, by ensuring that the user ID inside of the Docker container (for folders like /opt/airflow/) matches that of the local EC2 user (who is the owner of the local files airflow/ folder); this is basically telling the system that they are "same person", so allow Airflow from Docker container to write to local EC2 folders

### Walkthrough of docker-compose.yaml file
- The keyword "image" is when you want to pull a pre-made, generic image directly from Docker hub
- In contrast, "build" is used when you have a Dockerfile and need to create a custom image, which includes requirements.txt (and what other features are custom in this case?)
- (What are the consequences of using both "image" and "build" in the same docker-compose.yaml file? What kinds of errors would we get?)
- The container_name is optional, but highly recommended.  If we omit it, Docker will assign a generic, long name like airflow-setup-airflow-webserver-1.  By providing a simple container name, such as "airflow-webserver", it becomes much easier to run commands for a specific container, such as "docker logs airflow-webserver"
```
healthcheck:
  test: ["CMD", "curl", "--fail", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```
- A healthcheck is a small test that Docker runs periodically to check if your service is actually still working correctly.  For example, this healthcheck curls the webserver's endpoint, and checks if it returns a success code that indicates it is healthy. It runs this test every 30 seconds, Docker waits for 10 seconds for the test to finish before considering it a failure, and it needs to try (and fail) 3 times in a row before Docker marks the container as "unhealthy".
```
airflow-scheduler:
  ...
  restart: always
```
- This configuration tells Docker to restart the container if it ever stops for any reason (if the container crashes or if the host machine reboots).  This ensures that the scheduler or webserver are resilient and keep running, without manual intervention
- The "true" part in airflow users create is very important
- Othrwise, I will get an error like below, on my second run of the Docker container via "docker compose up", because on the first iteration "docker compose build; docker compose up", airflow init already created an admin user account, so the second time, it will run into a conflict
```
airflow-init-1       | joelu already exist in the db
airflow-init-1 exited with code 0
```

### Important: need a timeline of the "build" stage vs. "docker compose up" stage to explain what is happening at each step
- Phase 1: Build Time (docker compose build)
  - Docker-compose.yaml tells that we are will have a custom "build", because there is a "build" keyword instead of an pre-existing "image" keyword
  1. Dockerfile starts with apache/airflow:2.9.2
    - airflow user has UID 50000
    - /home/airflow owned by UID 50000
    - /opt/airflow owned by UID 50000
  2. ARG AIRFLOW_UID (receives 1000 from docker-compose, which receives it from credentials.env in turn)
  3. USER root
  4. RUN chown -R 1000:0 /home/airflow && chown -R 1000:0 /opt/airflow
    - Changes ownership of container's built-in directories to UID 1000 & group 0 (root group)
  5. RUN usermod --uid 1000 airflow  
    - Changes airflow user from UID 50000 → UID 1000
  6. COPY requirements.txt /requirements.txt
    - Copies from YOUR HOST to container during build
  7. RUN chown airflow:root /requirements.txt
    - Requirements.txt inside of the container becomes owned by airflow user with UID = 1000
  8. Switch back to USER airflow, from root, because we don't need to be root to pip install rqeuirements.txt
  9. RUN pip install --no-cache-dir -r /requirements.txt
    - Installs Python packages into the IMAGE
  10. NO VOLUMES MOUNTED YET!
    - Your host files are not accessible
    - Container only has its built-in files (I assume this means only /home/airflow/, config files, etc).  Host folders such as /dags, /config, etc. are not accessible during this build stage
    - Only the COPY command can bring files from the host to the container during build stage
  - Note: even though we have one dockerfile, Docker builds multiple images (one per service). Therefore, in the output, it will print out three separate exports, for example:
    - [airflow-init] exporting to image
    - [airflow-webserver] exporting to image  
    - [airflow-scheduler] exporting to image
  - Note: During the build process, to create an image, these can be done in any order. However, in the run stage, there is a clear dependency where airflow-init goes first
- Phase 2: Run Time (docker compose up)
  1. Container starts from our built image
    - airflow user is UID 1000 ✓
    - Built-in files owned by UID 1000 ✓
  2. Docker mounts your volumes:
    - Host: ./dags (UID 1000) → Container: /opt/airflow/dags (UID 1000) ✓
    - Host: ./logs (UID 1000) → Container: /opt/airflow/logs (UID 1000) ✓
  3. Container processes start:
    - Since webserver and scheduler depend on airflow init to complete successfully first, airflow init runs first, and then the other 2 follow afterward
    - airflow-init (UID 1000) can read/write mounted volumes, and kicks off the bash commands to create airflow user with username, password, first name, last name, email, etc. ✓
    - airflow-webserver (UID 1000) can read/write mounted volumes ✓
    - airflow-scheduler (UID 1000) can read/write mounted volumes ✓


### Troubleshooting error "psycopg2.errors.UndefinedColumn: column dag.dag_display_name does not exist"
- How do we resolve this error?
```
psycopg2.errors.UndefinedColumn: column dag.dag_display_name does not exist
```
- This is a database schema version mismatch issue:  Airflow 2.9.2 is trying to query a column that doesn't exist in your database
- This is not a permissions problem where Airflow cannot access RDS
- Verify that this column is indeed missing from table "dag". You shouldn't see this column listed:
```
select column_name from information_schema.columns
where table_name = 'dag'
order by column_name;
```
- The solution is to use an updated schema of Airflow tables, by changing "airflow db init" to "airflow db migrate":
```
  airflow-init:
    <<: *airflow-common
    command:
      - -c
      - |
        export PYTHONPATH=${PYTHONPATH:-}:/opt/airflow/etl_drivers:/opt/airflow/utils
        echo "Inside of container, running: airflow db migrate & airflow users create..."
        airflow db migrate && \
```
- In these cases, it is also possible that a prior version of the database was already created (AWS RDS already has existing tables created through airflow db init), and they will conflict with new tables / database version created by airflow db migrate
- Use this script to nuke the database and start from scratch. BE VERY CAREFUL - THIS WILL DELETE ALL PUBLIC SCHEMA INCLUDE OTHER TABLES
```
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
```

### The two reset scripts for cleaning the RDS database:
```
-- -------------------------------------------------------------------
-- SCRIPT #1: SELECTIVE TABLE CLEANUP (Airflow-Only Reset)
-- -------------------------------------------------------------------
-- 
-- WHAT IT DOES:
-- - Drops only Airflow-specific metadata tables
-- - Preserves the database schema and any non-Airflow tables
-- - Maintains database users, permissions, and other database objects
-- 
-- WHEN TO USE:
-- - After a failed or inconsistent Airflow setup
-- - To resolve issues related to stale data, especially after changing
--   the Fernet key
-- - When you need to start Airflow with a clean slate but want to
--   preserve other database objects (views, functions, non-Airflow tables)
-- - When you share the database with other applications
-- 
-- ADVANTAGES:
-- - Surgical approach - only affects Airflow
-- - Preserves database permissions and users
-- - Safer for shared database environments
-- - No need to re-grant schema permissions
-- 
-- DISADVANTAGES:
-- - Must manually list all Airflow tables (could miss new ones in future versions)
-- - Less thorough than schema reset
-- - Won't fix schema-level permission issues
-- 
-- HOW TO USE:
-- 1. Connect to your AWS RDS PostgreSQL database using pgAdmin4
-- 2. Execute this entire script
-- 3. Restart Airflow services: docker compose up -d
-- 4. The airflow-init service will recreate all tables with current schema

DROP TABLE IF EXISTS "job" CASCADE;
DROP TABLE IF EXISTS "slot_pool" CASCADE;
DROP TABLE IF EXISTS "log" CASCADE;
DROP TABLE IF EXISTS "dag_code" CASCADE;
DROP TABLE IF EXISTS "dag_pickle" CASCADE;
DROP TABLE IF EXISTS "ab_user" CASCADE;
DROP TABLE IF EXISTS "ab_register_user" CASCADE;
DROP TABLE IF EXISTS "connection" CASCADE;
DROP TABLE IF EXISTS "variable" CASCADE;
DROP TABLE IF EXISTS "dag_schedule_dataset_reference" CASCADE;
DROP TABLE IF EXISTS "task_outlet_dataset_reference" CASCADE;
DROP TABLE IF EXISTS "dag_run" CASCADE;
DROP TABLE IF EXISTS "dag_tag" CASCADE;
DROP TABLE IF EXISTS "dag_owner_attributes" CASCADE;
DROP TABLE IF EXISTS "ab_permission" CASCADE;
DROP TABLE IF EXISTS "ab_permission_view" CASCADE;
DROP TABLE IF EXISTS "ab_view_menu" CASCADE;
DROP TABLE IF EXISTS "ab_user_role" CASCADE;
DROP TABLE IF EXISTS "ab_role" CASCADE;
DROP TABLE IF EXISTS "dag_warning" CASCADE;
DROP TABLE IF EXISTS "dagrun_dataset_event" CASCADE;
DROP TABLE IF EXISTS "task_instance" CASCADE;
DROP TABLE IF EXISTS "dag_run_note" CASCADE;
DROP TABLE IF EXISTS "ab_permission_view_role" CASCADE;
DROP TABLE IF EXISTS "task_fail" CASCADE;
DROP TABLE IF EXISTS "task_map" CASCADE;
DROP TABLE IF EXISTS "task_reschedule" CASCADE;
DROP TABLE IF EXISTS "xcom" CASCADE;
DROP TABLE IF EXISTS "task_instance_note" CASCADE;
DROP TABLE IF EXISTS "session" CASCADE;
DROP TABLE IF EXISTS "alembic_version" CASCADE;
```

```
-- -------------------------------------------------------------------
-- SCRIPT #2: COMPLETE SCHEMA RESET (Nuclear Option)
-- -------------------------------------------------------------------
-- 
-- WHAT IT DOES:
-- - Completely destroys and recreates the 'public' schema
-- - Removes ALL tables, views, functions, sequences, and data
-- - Resets all permissions to defaults
-- 
-- WHEN TO USE:
-- - When you have irrecoverable database corruption
-- - After major Airflow version upgrades with migration issues
-- - When Script #1 doesn't resolve the problem
-- - When you want to guarantee a completely fresh start
-- - When the database is dedicated solely to Airflow
-- 
-- ADVANTAGES:
-- - Most thorough reset possible
-- - Guaranteed to fix any schema inconsistencies
-- - Automatically handles all database objects
-- - Future-proof (works regardless of Airflow version changes)
-- 
-- DISADVANTAGES:
-- - Destroys ALL data in the public schema (not just Airflow)
-- - Removes any custom database objects you may have created
-- - Requires re-granting permissions to your database user
-- - More disruptive than selective approach
-- 
-- HOW TO USE:
-- 1. Connect to your AWS RDS PostgreSQL database using pgAdmin4
-- 2. Execute this entire script
-- 3. If you get "role postgres does not exist" error, replace 'postgres' 
--    with your actual database username (e.g., 'joelu')
-- 4. Restart Airflow services: docker compose up -d

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Grant permissions to standard postgres user (if it exists)
-- Note: This may fail on AWS RDS where 'postgres' user doesn't exist
GRANT ALL ON SCHEMA public TO postgres;

-- Grant permissions to public (required for proper schema access)
GRANT ALL ON SCHEMA public TO public;

-- If the postgres grant failed, uncomment and modify the line below
-- with your actual database username:
-- GRANT ALL ON SCHEMA public TO joelu;
```

### Commands for building and starting up Docker containers
```
docker compose down --volumes --remove-orphans
```
- Stops and removes containers
- --volumes: deletes persistent data (logs, database data, etc) for a truly clean start
- --remove-orphans: removes containers not in current compose file, i.e. - removes old containers from previous versions of compose file (if we've changed docker-compose.yaml)
```
docker system prune -f
```
- Removes unused containers, unused networks, dangling images, build cache
- -f means force (don't ask for confirmation)
```
docker compose build --no-cache
```
- Builds images from scratch, ignores all cached layers

### Add a section for resetting all Airflow-related AWS RDS tables, in cases where:
- When should we use this option?
- (See the comments in the reset_airflow.sql for proper usage)

### Choosing either build or image, but not both
```
x-airflow-common:
  &airflow-common
  build:
    context: .
    dockerfile: Dockerfile.airflow  
  image: apache/airflow:2.8.1
```
This causes conflicts, because image is saying to use specifically this version of airflow, from version 2.8.1, whereas build is using a customization defined in the Dockerfile.  Solution needs to remove the image portion
- When you provide both build and image in docker-compose.yaml, Docker's behavior can be unpredictable. Often, it will prioritize the image tag, pull the generic image from Docker Hub, and completely ignore your build section. This means your custom Dockerfile never ran, and the libraries in your requirements.txt were never installed, leading to "module not found" errors later. 

### A discussion of YAML anchors
```
<<: *airflow-base
```
(I believe that defining this at the top, and then referring to it under webserver and scheduler services basically means that I am inserting this block of code, from build, to volumes, basically gets subtituted into the services section)
I can ask Claude for an example to show me what it looks like, without the anchor, such that the full contents are replicated twice, and written explicitly in the webserver and scheduler section

### The importance of the FERNET KEY
```
Running: docker compose up...
[+] Running 4/4
 ✔ Network airflow_default                Created                                                                       0.1s 
 ✔ Container airflow-airflow-init-1       Created                                                                       0.1s 
 ✔ Container airflow-airflow-webserver-1  Created                                                                       0.1s 
 ✔ Container airflow-airflow-scheduler-1  Created                                                                       0.1s 
Attaching to airflow-init-1, airflow-scheduler-1, airflow-webserver-1
airflow-init-1       | Inside of container, running: airflow db migrate & airflow users create...
airflow-init-1       | DB: postgresql+psycopg2://joelu:***@postgresql-db.cjsyoeie2jow.us-east-2.rds.amazonaws.com:5432/postgres
airflow-init-1       | Performing upgrade to the metadata database postgresql+psycopg2://joelu:***@postgresql-db.cjsyoeie2jow.us-east-2.rds.amazonaws.com:5432/postgres
airflow-init-1       | INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
airflow-init-1       | INFO  [alembic.runtime.migration] Will assume transactional DDL.
airflow-init-1       | ✅ Loaded environment variables from /opt/.env (Docker container)
airflow-init-1       | ✅ Connected successfully!
airflow-init-1       | Database migrating done!
airflow-init-1       | /home/airflow/.local/lib/python3.8/site-packages/flask_limiter/extension.py:336 UserWarning: Using the in-memory storage for tracking rate limits as no storage was explicitly specified. This is not recommended for production use. See: https://flask-limiter.readthedocs.io#configuring-a-storage-backend for documentation about configuring the storage backend.
airflow-init-1       | [2025-08-14T22:01:18.024+0000] {override.py:868} WARNING - No user yet created, use flask fab command to do it.
airflow-init-1       | User "joelu" created with role "Admin"
airflow-init-1 exited with code 0
airflow-webserver-1  | 
airflow-scheduler-1  | 
airflow-webserver-1  | [2025-08-14T22:01:39.988+0000] {configuration.py:2065} INFO - Creating new FAB webserver config file in: /opt/airflow/webserver_config.py
airflow-webserver-1  | ERROR: You need to initialize the database. Please run `airflow db init`. Make sure the command is run using Airflow version 2.8.1.
airflow-webserver-1 exited with code 1
```
- How do I know the cause was a missing fernet key?
- Our logs clearly showed Database migrating done! and User "joelu" created with role "Admin". This is proof that the init container successfully connected to the database, created all the tables, and added the user. At this point, the database is technically "initialized."
- The webserver then started and immediately threw the error ERROR: You need to initialize the database. This creates a logical contradiction. How can the database be both initialized and not initialized at the same time?
- The Contradiction Points to a Configuration Mismatch: When two components look at the same data source but see different things, it almost always points to a problem with their configuration, not the data source itself. Both containers used the same database connection string, so the problem had to be something else that would cause one to see the world differently from the other.
- What is the issue here?
  - Database Connection? No, the logs show both containers successfully connecting.
  - Executor Type? No, that wouldn't affect reading the database schema.
  -Encryption Key? Yes. The fernet key is used to encrypt and decrypt sensitive data stored in the database, like connection passwords.
- So here is what happened:
  - The airflow-init container starts, generates a temporary fernet key (Key A), and uses it to encrypt some default data in the database.
  - The airflow-webserver container starts, generates its own temporary fernet key (Key B), and tries to read the database.
  - When the webserver tries to decrypt the data written by the init container, it fails because Key B cannot decrypt data encrypted with Key A.
- Solution:
  - Generate a fernet key like this:
    ```
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```
  - Add the fernet key to the credentials.env file
  - Add it to the docker-compose.yaml file:
    ```
    environment:
      &airflow-env
      # ... your other environment variables ...
      AIRFLOW__CORE__FERNET_KEY: '${_FERNET_KEY}'
      # ... your other environment variables ...
    ```
- The fact it is saying "Creating new FAB webserver config file..." also means that airflow-init created essential config file such as airflow.cfg in the /opt/airflow directory, but airflow-webserver is unable to access that one, due to missing fernet key, so it creates its own airflow.cfg file, causing this message to appear
What is the airflow.cfg file?
- The airflow.cfg file is the main configuration file for Airflow. It contains hundreds of settings that control nearly every aspect of Airflow's behavior, organized into sections like [core], [webserver], [scheduler], and [database].  Think of it as Airflow's central nervous system. It's where you define key parameters, including: - executor: Which executor to use (LocalExecutor, CeleryExecutor, etc.).
- sql_alchemy_conn: The connection string for the metadata database.
- fernet_key: The encryption key for secrets.
- dags_folder: The path to your DAG files.
- load_examples: Whether to load the example DAGs.
- Airflow-init also creates webserver_config.py 
- Both the airflow.cfg and webserver_config.py are created by airflow init, and mirrored onto local /config folder through volume mounts.  When airflow-webserver starts after that, it looks inside of /opt/airflow/config and finds these configuration files left there earlier than init container

### Difference between AIRFLOW__WEBSERVER__SECRET_KEY vs. AIRFLOW__CORE__FERNET_KEY
- AIRFLOW__CORE__FERNET__KEY is used for encryption at rest.  It encrypts sensitive information before it is saved to the Airflow metadata database.  It protects secrets (like passwords, keys, tokens) inside of your database.  If someone gained access to a backup of your database, they would not be able to read these secrets without the Fernet key
- AIRFLOW__WEBSEVER__SECRET_KEY is used for securing user sessions in transit.  Its job is to sign the browser cookie that Airflow webserver gives you after you log in.  This protects the integrity of the user's logged-in session while they are actively using the Airflow UI

### Section on the virtual environment requirements
- If I am setting up this project, do I need a virtual enviroment?  Airflow already runs inside of a Docker container, and pulls the dependencies from requirements.txt, so isn't that already sufficient? 
  - (Yes, but I think the answer is - once I start adding in DAGs which are pieces of Python code, I would like to keep the dependencies required to develop those DAGs in a self-contained environment)
  - Additionally, should the virtual environment have the same requirements.txt as the Docker container? For now, yes.  But in the future, let's say that you add in a FastAPI folder under financial-etl-poc. Then we need the virtual environment for the project to be the superset of the requirements.txt for the Dockerized Airflow and Dockerized FastAPI pieces

```
cd ~/financial-etl-poc
python3 -m venv .venv
source .venv/bin/activate
```

### Section on resolving RDS AWS
- Issue: when you run
```
(.venv) your_linux_username: ~/financial-etl-poc/airflow$ docker compose build
```
You will get:
```
WARN[000] The "rds_username" variable is not set. Defaulting to blank string.
WARN[000] The "rds_password" variable is not set. Defaulting to blank string.
WARN[000] The "rds_host" variable is not set. Defaulting to blank string.
WARN[000] The "rds_port" variable is not set. Defaulting to blank string.
```
- The core issue is that the credentials.env file is located under financial-etl-poc/, but the files that need it are located under financial-etl-poc/
- You can move the credientials.env into airflow/ folder but this doesn't make sense, because other components of this project later on (such as data engineering scripts under financial-etl-poc/etl_drivers/ folder) will need those same credentials, so it makes sense to keep credientials.env under financial-etl-poc/ instead of moving it to financial-etl-poc/airflow/
- Even if you say in the docker-compose.yaml:
  env_file:
  - ../credentials.env
  In theory, it should go up one level from financial-etl-poc/airflow/ folder to financial-etl-poc/ folder and find credentials.env, but it still does not
- The reason is because Docker Compose can only interpolate ${VAR_NAME} via the actual shell environment or an .env file in the same directory as the docker-compose.yaml file. For example, if docker-compose.yaml requires rds_username and rds_password (below code block), and it is located in financial-etl-poc/airflow/ folder, credentials.env needs to be the same financial-etl-poc/airflow/ folder 
```
  environment:
    # Extract credentials such as RDS username and password from .env file, to connect to PostgreSQL database
    - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${rds_username}:${rds_password}@${rds_host}:${rds_port}/${rds_dbname}
```
- The Docker Compose file docker-compose.yaml cannot interpolate/resolve the credientials from an .env file which resides in a different folder.  Since credentials is actually located in financial-etl-poc/, docker-compose.yaml cannot resolve (do the substitution) properly
- The solution was to inject the credentials using Linux shell environment: export $(cat ../credentials.env | xargs)
- Explanation:

This reads the contents of credentials.env file
```
cat ../credentials.env
```

This takes the multi-line output and turns it into a single space-separated line
```
rds_username=my_username rds_password=my_password rds_port=1234
```

This sets environment variables in the shell
```
export $(...)
# Equivalent to:
export rds_username=my_username rds_password=my_password rds_port=1234
```

### Error: service "airflow-init" depends on undefined service "postgres"
```
airflow-init:
  image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.8.1} 
  depends_on: 
    postgres: 
      condition: service_healthy
```
- Some online tutorials might suggest this block in the docker-compose.yaml file, but this requires a local postgres service, and it needs to be defined in the services section
- Since we already have an existing AWS RDS instance, this section is unnecessary and needs to be removed

### Entry points in the docker-compose.yaml file
```
  airflow-init:
    entrypoint: /bin/bash
    command:
      - -c
      - |
        airflow db migrate
        airflow users create \
          --username ${AIRFLOW_USERNAME} \
          --password ${AIRFLOW_PASSWORD} \
          ...
  airflow-webserver:
    ...
    container_name: airflow_webserver
    command: airflow webserver
    ...
```
- Question: Why does airflow init has an entrypoint defined as /bin/bash, whereas the other 2 services webserver and scheduler do not have entrypoints listed?
- The Airflow Docker image already has a default, build-in entrypoint that: sets up environmental variables, waits for the database to be ready, and then runs whatever command you pass to it
- Webserver and scheduler use this default entrypoint because we can launch them with a simple, single command, like "airflow webserver" or "airflow scheduler". It's one line only, and it does not require complex logic for handling "if this command A fails, then run this other command B..."
- In contrast, for airflow-init, we need to:
  - Run multiple commands in sequence: first "airflow db migrate", then "airflow users create..."
  - Pass multi-line scripts: define username, password, email, etc.
    ```
    airflow users create \
    --username ${AIRFLOW_USERNAME} \
    --password ${AIRFLOW_PASSWORD} \
    ...
    ```
  - Leverage shell features, such as || for error handling: if airflow user already exists, then don't re-create the same user and just return true/success
    ```
    airflow users create ... || true
    ```
- Therefore, the default entrypoint is not sufficient for our needs in airflow init, and we have to override the default entry, and create our own custom one. We set the entry point to /bin/bash, use -c flag to say "whatever string that follows needs to be executed as a shell script" and |- is YAML syntax to define a multi-line string. Through this, we are able to: execute multiple commands in sequence, run a multi-line shell script, and handle bash's if/else logic in our entrypoint command


### UID and permissions in mounted folders issue
- When Airflow runs inside of a Docker container, a one-to-one mapping is created between local folders (on my EC2) and the container folders (inside of Docker container).   such that when the contents of container folders such as opt/airflow/dags or opt/airflow/logs become linked to mounted directories (inside of container) such as opt/airflow/dags, opt/airflow/logs. 
- Explain why AIRFLOW_UID=1000
- Interestingly, in our dockerfile, we have as our solution (our default Linux user ID that is not root is normally 1000, and we are changing the airflow folder inside of the container to be owned by 1000):
RUN chown -R ${AIRFLOW_UID}:0 /home/airflow
- But in a prior discussion with ChatGPT, they suggested going the other way around (the airflow default user ID is 50000, and it told me to change the permissions of my folders to 50000 to match default airflow ID)
sudo chown -R 50000:0 dags/ plugins/ scripts/ utils/
- Explain -R recursive
- Explain group ID vs user ID

### Why doesn't the credentials.env file need to be mounted under volumes section?
- The env_file directive is the correct, secure way to load variables. Mounting the file itself (volumes: - ../.env:/opt/.env) unnecessarily exposes your raw credentials file inside the container's filesystem, which is a security risk. Stick to using only env_file
What happens with the .env file:
- At container startup, Docker reads credentials.env from local file system
- Docker parses the file and extracts the environmental variables, such as rds_username, rds_password, etc.
- Docker injects those variables into the container's environment
Therefore, the file itself is never copied into the container; the container only receives the environmental variables, not the actual file.  The environmental variables are safer than the .env file because:
- A malicious agent cannot search for an .env file in file system (it doesn't exist)
- A malicious agent must know the exact variable name, such as $RDS_USERNAME
- Other containers cannot see it


### Section on the "docker build" timeline and the "docker up/run" timeline

### To do:
- Can we setup airflow using "airflow db init" just once, and throw it away using "docker compose run --rm" (remove, as in, temporary container)?  Because right now, the current setup has airflow init listed under services section, so doesn't it run "airflow init" every time that I wake up the containers using "docker compose up"?  Maybe that is what happens, but it skips initialization because it sees that user already exists, so it's fine, it's not re-creating a new admin account everytime, right?
- What is the role of entrypoint: /bin/bash, and why is it only listed under airflow-init section, but not listed under webserver or scheduler sections?
- Discuss more about build vs. image
- Need to discuss YAML anchors, which are a block of config that avoids duplication. Example: &airflow-common

### After adding DAGs later on:
- Check with Claude Opus how I need to modify my Python scripts to have conditional sys.path.append statements. Depending on whether or not I am running the Python script from local folder in EC2 vs. inside of Docker container (if /opt/airflow exists), sys.path.append(...) should append either:
  - the project_root_folder (if local) or 
  - /opt/airflow (if inside of container)
- I also need to mount my credentials.env into the Docker container as well?

(To preview how these notes look, press Ctrl+Shift+V)