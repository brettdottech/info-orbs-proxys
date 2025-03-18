# ===========
# INSTALL
# ===========
# Build
docker build -t orbs-proxy .

# Install (daemon mode, listen at host's port 8021)
docker run -d -p 8021:8080 --restart unless-stopped --name orbs-proxy orbs-proxy


# ===========
# UPDATE
# ===========
docker stop orbs-proxy
docker rm orbs-proxy
docker build -t orbs-proxy .
docker run -d -p 8021:8080 --restart unless-stopped --name orbs-proxy orbs-proxy


# OPTIONAL: USE DOCKER VOLUMES for faster development (this will use the .py directly)
docker run -d -p 8021:8080 --restart unless-stopped --name orbs-proxy -v "$(pwd):/app" orbs-proxy




# ===========
# CHECK
# ===========
# Check logs
docker logs tempest-proxy

# Check running processes
docker ps
