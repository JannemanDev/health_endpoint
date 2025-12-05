# Installation

```bash
# stop and remove any previous container
sudo docker stop health_server
sudo docker rm health_server

# build image
sudo docker build -t health_server:latest .


# writable /tmp using tmpfs
# first port is external, second port is internal
sudo docker run -d --name health_server -p 9000:8000 --read-only --tmpfs /tmp --cap-drop ALL health_server:latest

# check logs
docker logs health_server

```