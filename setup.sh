#!/bin/bash
set -e

# Add Microsoft keys and repo for msodbcsql18
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

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
