#!/bin/bash
set -e

# Update system packages
apt-get update

# Install required ODBC components and pre-accept Microsoft EULA
ACCEPT_EULA=Y apt-get install -y \
    unixodbc \
    unixodbc-dev \
    msodbcsql18 \
    curl \
    gnupg

# Verify installation
echo "Installed ODBC drivers:"
odbcinst -q -d
