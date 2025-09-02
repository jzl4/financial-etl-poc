#!/bin/bash
# Shebang to tell Linux OS to use bash interpreter

# Export environment variables
export $(cat ../credentials.env | xargs)

# --volumes     Removes persistent data (logs, database data, etc)
# --remove-orphans  Removes old containers from previous versions of compose file
docker compose down --volumes --remove-orphans
# Removes unused containers, networks, images, build cache.  -f     Force it, don't ask for confirmation
docker system prune -f

# --no-cache    Build from scratch, ignore all cached layers
docker compose build --no-cache

# Once the build succeeds, start the services
docker compose up -d
