docker stop health_server
docker rm health_server

docker build -t health_server:latest .

docker run -d --name health_server -p 9000:8000 --read-only --tmpfs /tmp --cap-drop ALL health_server:latest

docker logs health_server
