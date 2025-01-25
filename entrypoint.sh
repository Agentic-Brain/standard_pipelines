#!/bin/bash

# Function to read Docker secret and set as environment variable
read_secret() {
    local secret_path=$1
    # Get just the filename from the path
    local secret_name=$(basename "$secret_path")
    
    # Get project name from FLASK_APP environment variable
    local project_prefix=$(echo "$FLASK_APP" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    
    # Remove project prefix from secret name
    if [[ "$secret_name" == "${project_prefix}_"* ]]; then
        # Remove project prefix and convert to uppercase
        local env_var_name=$(echo "$secret_name" | sed "s/^${project_prefix}_//" | tr '[:lower:]' '[:upper:]')
        
        if [ -f "$secret_path" ]; then
            export "${env_var_name}"="$(cat "$secret_path")"
            echo "Loaded secret: ${secret_name} as ${env_var_name}"
        else
            echo "Warning: Secret file ${secret_path} not found"
        fi
    else
        echo "Warning: Secret ${secret_name} does not have expected prefix ${project_prefix}_"
    fi
}

# Verify FLASK_APP is set
if [ -z "$FLASK_APP" ]; then
    echo "Error: FLASK_APP environment variable must be set"
    exit 1
fi

# Read all secrets from /run/secrets directory
echo "Loading Docker secrets as environment variables..."
if [ -d "/run/secrets" ]; then
    for secret_file in /run/secrets/*; do
        if [ -f "$secret_file" ]; then
            read_secret "$secret_file"
        fi
    done
else
    echo "Warning: No /run/secrets directory found"
fi

# Execute the passed command (usually the application start command)
exec "$@" 