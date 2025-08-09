# Use the official Microsoft Python image (Debian Bullseye based)
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Set the working directory
WORKDIR /home/vscode/python

# Node.jsのインストール（最新LTS v22）
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs

RUN npm install -g \
    @anthropic-ai/claude-code  

# Install Python packages that are commonly used
RUN pip install --upgrade pip

# Keep the container running
CMD ["sleep", "infinity"]