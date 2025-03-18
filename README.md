# Simple GLobal Proxy For Info Orbs

## INSTALL

### Build

```
docker build -t tempest-proxy .
```

### Install (daemon mode, listen at host's port 8021)

```
docker run -d -p 8021:8080 --restart unless-stopped --name orbs-proxy orbs-proxy
```

## UPDATE

```
docker stop orbs-proxy
docker rm orbs-proxy
docker build -t orbs-proxy .
docker run -d -p 8021:8080 --restart unless-stopped --name orbs-proxy orbs-proxy
```

## OPTIONAL: USE DOCKER VOLUMES for faster development (this will use the .py directly)

```
docker run -d -p 8021:8080 --restart unless-stopped --name orbs-proxy -v "$(pwd):/app" orbs-proxy
```

## See

- https://github.com/brettdottech/info-orbs
- https://tempest.earth/
- https://tempestwx.com/map/

## License

This software is distributed under MIT license. See LICENSE.txt for details.
