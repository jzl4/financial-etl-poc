


- This assumes that you already have an existing AWS RDS database

## Project Structure
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

### Section explaining what each of these pieces mean
- Explain what is usually inside of config, dags, logs, plugins, etc.
- Explain what credientials.env contains.  Example: rds_username = blah blah, rds_password = blah blah

### Important: need a section explaining what each of the pieces inside of the Dockerfile, docker-compose.yaml, and requirements.txt mean
- The "true" part in airflow users create is very important
- Othrwise, I will get an error like below, on my second run of the Docker container via "docker compose up", because on the first iteration "docker compose build; docker compose up", airflow init already created an admin user account, so the second time, it will run into a conflict
```
airflow-init-1       | joelu already exist in the db
airflow-init-1 exited with code 0
```

### Add a section for reseting all Airflow-related AWS RDS tables, in cases where:
- When should we use this option?
- (See the comments in the reset_airflow.sql for proper usage)

### Important: need a timeline of the "build" stage vs. "docker compose up" stage to explain what is happening at each step

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

(To preview how these notes look, press Ctrl+Shift+V)

### After adding DAGs later on:
- Check with Claude Opus how I need to modify my Python scripts to have conditional sys.path.append statements. Depending on whether or not I am running the Python script from local folder in EC2 vs. inside of Docker container (if /opt/airflow exists), sys.path.append(...) should append either:
  - the project_root_folder (if local) or 
  - /opt/airflow (if inside of container)
- I also need to mount my credentials.env into the Docker container as well?

