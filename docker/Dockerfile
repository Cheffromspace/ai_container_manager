FROM python:3.10-slim

# Install necessary dependencies
RUN apt-get update && \
    apt-get install -y curl git nodejs npm openssh-server sudo && \
    pip install --no-cache-dir requests flask gunicorn && \
    mkdir -p /workspace /run/sshd && \
    echo 'root:password' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

WORKDIR /workspace

# Copy application files following new directory structure
COPY ./core /app/core/
COPY ./utils /app/utils/
COPY ./debug /app/debug/
COPY ./docker /app/docker/
COPY ./docs /app/docs/
COPY ./tests /app/tests/
COPY ./run.py /app/
COPY ./__init__.py /app/
COPY ./docker_wrapper.sh /app/
COPY ./requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Ensure wrapper script is executable
RUN chmod +x /app/docker_wrapper.sh

# Expose API and SSH ports
EXPOSE 5000 22

# Copy app.py to the root level as a workaround for module imports
COPY ./core/app.py /app/app.py

# Start both the API server and SSH server
CMD ["sh", "-c", "/usr/sbin/sshd && cd /app && python app.py"]