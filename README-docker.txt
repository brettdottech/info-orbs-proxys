# ===========
# INSTALL
# ===========
# Build
docker build -t tempest-proxy .

# Install (daemon mode, listen at host's port 8021)
docker run -d -p 8021:8080 --restart unless-stopped --name tempest-proxy tempest-proxy


# ===========
# UPDATE
# ===========
docker stop tempest-proxy
docker rm tempest-proxy
docker build -t tempest-proxy .
docker run -d -p 8021:8080 --restart unless-stopped --name tempest-proxy tempest-proxy


# OPTIONAL: USE DOCKER VOLUMES for faster development (this will use the .py directly)
docker run -d -p 8021:8080 --restart unless-stopped --name tempest-proxy -v "$(pwd):/app" tempest-proxy




# ===========
# CHECK
# ===========
# Check logs
docker logs tempest-proxy

# Check running processes
docker ps
