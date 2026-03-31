docker stop health_server
docker rm health_server
sudo docker run -d \
	--name health_server \
	--restart unless-stopped \
	-p 9001:8000 \
	--read-only \
	--tmpfs /tmp \
	--cap-drop ALL \
	health_server:latest

