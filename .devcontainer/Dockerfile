# Use the official Microsoft Dev Container base image (Ubuntu)
FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Install essential build tools and utilities including Python
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    jq \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.11 explicitly (align with CI)
RUN add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3.11-distutils && \
    rm -rf /var/lib/apt/lists/* && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Install Terraform using binary download (more reliable than APT)
RUN TERRAFORM_VERSION="1.13.1" && \
    wget -O /tmp/terraform.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" && \
    unzip /tmp/terraform.zip -d /usr/local/bin && \
    rm /tmp/terraform.zip && \
    chmod +x /usr/local/bin/terraform

# The vscode user already exists in the base image, just ensure sudo access
RUN echo "vscode ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/vscode && \
    chmod 0440 /etc/sudoers.d/vscode

# Set working directory
WORKDIR /workspaces

# Copy only essential files for build caching
COPY .devcontainer/ .devcontainer/
COPY infra/ infra/

# Switch to non-root user early for better permission handling
USER $USERNAME

# Set default shell
SHELL ["/bin/bash", "-c"]
