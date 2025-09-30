#!/bin/bash

set -e  # Exit immediately on error

NETWORK_NAME="mu-python-network"

# Create the network if it doesn't exist
if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
  echo " Creating Docker network: ${NETWORK_NAME}"
  docker network create "${NETWORK_NAME}"
else
  echo "Docker network '${NETWORK_NAME}' already exists."
fi