FROM python:3.10-slim

# Install necessary dependencies
RUN apt-get update && \
    apt-get install -y curl git nodejs npm openssh-server sudo && \
    pip install --no-cache-dir requests flask gunicorn && \
    mkdir -p /workspace /run/sshd && \
    echo 'root:password' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

WORKDIR /workspace

# Copy application files
COPY app.py /app/
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Expose API and SSH ports
EXPOSE 5000 22

# Start both the API server and SSH server
CMD ["sh", "-c", "/usr/sbin/sshd && cd /app && gunicorn -b 0.0.0.0:5000 app:app"]