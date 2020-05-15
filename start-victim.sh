#!/bin/bash

DOCKER_ID=$(sudo docker ps -a | grep victim | cut -d' ' -f1)
sudo docker exec -it $DOCKER_ID /bin/bash
