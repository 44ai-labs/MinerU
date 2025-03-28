#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# in CI we use the default namespace, locally mineru

NAMESPACE="${NAMESPACE:-default}"

# Get the head pod name
POD=$(kubectl get pods -l app=mineru-44ai -o custom-columns=POD:metadata.name --no-headers -n $NAMESPACE)

if [ -z "$POD" ]; then
  echo "No pod found with label app=mineru-44ai in namespace $NAMESPACE"
  exit 1
fi

echo "Copying logs from head pod $POD"

# Define the local destination directory
LOCAL_DIR="./logs"

# Ensure the local directory exists
mkdir -p $LOCAL_DIR

# Retrieve the logs from the pod and save them to a file.
LOG_FILE="$LOCAL_DIR/mineru-44ai.log"
kubectl logs "$POD" -n "$NAMESPACE" > "$LOG_FILE"

echo "Logs have been copied to $LOG_FILE"
