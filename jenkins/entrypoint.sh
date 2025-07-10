#!/bin/bash 
set -e 
 
echo "Checking Docker socket permissions..." 
 
if [ -S /var/run/docker.sock ]; then 
    echo "Docker socket found. Fixing permissions..." 
    sudo chown root:docker /var/run/docker.sock 
    sudo chmod 664 /var/run/docker.sock 
    echo "Docker socket permissions fixed" 
else 
    echo "Warning: Docker socket not found!" 
fi 
 
echo "Starting Jenkins..." 
exec /usr/bin/tini -- /usr/local/bin/jenkins.sh 
