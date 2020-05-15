#/bin/bash

DOCKER_ID=$(sudo docker ps -a | grep attacker | cut -d' ' -f1)
sudo docker exec -it $DOCKER_ID /bin/bash
