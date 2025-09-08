


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
  In theory, it should go up one level from financial-etl-poc/airflow/ folder to financial-etl-poc/ folder and find credentials.env, but it still does not.  (Why?)
- The solution was to inject the credentials using Linux CLI: export $(cat ../credentials.env | xargs)

### Section explaining the UID and permissions in mounted folders issue
- Explain why AIRFLOW_UID=1000
- Interestingly, in our dockerfile, we have as our solution (our default Linux user ID that is not root is normally 1000, and we are changing the airflow folder inside of the container to be owned by 1000):
RUN chown -R ${AIRFLOW_UID}:0 /home/airflow
- But in a prior discussion with ChatGPT, they suggested going the other way around (the airflow default user ID is 50000, and it told me to change the permissions of my folders to 50000 to match default airflow ID)
sudo chown -R 50000:0 dags/ plugins/ scripts/ utils/
- Explain -R recursive
- Explain group ID vs user ID

### Section on the "docker build" timeline and the "docker up/run" timeline

### To do:
- Discuss more about build vs. image
- Need to discuss YAML anchors, which are a block of config that avoids duplication. Example: &airflow-common

(To preview how these notes look, press Ctrl+Shift+V)