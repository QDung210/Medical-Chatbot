FROM jenkins/jenkins:lts

USER root

RUN apt-get update && \
    apt-get install -y docker.io && \
    apt-get install -y git sudo && \
    apt-get clean

RUN curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Allow Jenkins to use Docker
RUN groupadd docker || true && \
    usermod -aG docker jenkins

# Allow Jenkins user to run sudo without a password
RUN echo "jenkins ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/jenkins
RUN chmod 0440 /etc/sudoers.d/jenkins

# Create entrypoint script directly in Dockerfile
RUN printf '#!/bin/bash\n\
set -e\n\
\n\
echo "Checking Docker socket permissions..."\n\
\n\
if [ -S /var/run/docker.sock ]; then\n\
    echo "Docker socket found. Fixing permissions..."\n\
    sudo chown root:docker /var/run/docker.sock\n\
    sudo chmod 664 /var/run/docker.sock\n\
    echo "Docker socket permissions fixed"\n\
else\n\
    echo "Warning: Docker socket not found!"\n\
fi\n\
\n\
echo "Starting Jenkins..."\n\
exec /usr/bin/tini -- /usr/local/bin/jenkins.sh\n' > /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

USER jenkins

# Jenkinsfile sẽ được mount bởi docker-compose volume, không cần COPY

# Switch back to root to modify user groups
USER root
RUN usermod -aG docker jenkins
RUN usermod -aG root jenkins

# Switch back to jenkins user
USER jenkins

EXPOSE 8080 50000

# Use entrypoint script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]