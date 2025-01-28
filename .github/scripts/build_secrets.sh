#!/bin/bash

# Ensure the script is called with two arguments
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <project_name> <environment_type>"
  exit 1
fi

PROJECT_NAME=$1
ENVIRONMENT_TYPE=$(echo "$2" | tr '[:lower:]' '[:upper:]') # Convert environment type to uppercase

# Get project ID from project list
PROJECT_ID=$(bws project list | jq -r --arg name "$PROJECT_NAME" '.[] | select(.name == $name) | .id')

if [ -z "$PROJECT_ID" ]; then
  echo "Project '$PROJECT_NAME' does not exist. Creating it now..."
  PROJECT_ID=$(bws project create "$PROJECT_NAME" | jq -r '.id')
else
  echo "Project '$PROJECT_NAME' already exists with ID $PROJECT_ID."
fi

# Function to create a secret if it does not already exist
create_secret_if_not_exists() {
  local SECRET_NAME=$1
  local GENERATE_VALUE=${2:-true}  # Default to true if not specified
  local PROJECT_ID=$3
  local DEFAULT_VALUE=${4:-""}     # Default empty if not specified

  # Check if secret already exists
  SECRET_EXISTS=$(bws secret list "$PROJECT_ID" | jq -r --arg name "$SECRET_NAME" '.[] | select(.key == $name)')
  
  if [ -n "$SECRET_EXISTS" ]; then
    echo "Secret $SECRET_NAME already exists. Skipping."
    return 0
  fi

  # Generate or use default value
  local SECRET_VALUE
  if [ "$GENERATE_VALUE" = true ]; then
    SECRET_VALUE=$(openssl rand -base64 32)
  else
    SECRET_VALUE="$DEFAULT_VALUE"
  fi

  # Convert value to lowercase
  SECRET_VALUE=$(echo "$SECRET_VALUE" | tr '[:upper:]' '[:lower:]')

  if [ -z "$SECRET_VALUE" ]; then
    echo "Error: Value for secret $SECRET_NAME is empty. Skipping creation."
    return 1
  fi

  echo "Creating secret: $SECRET_NAME"
  bws secret create "$SECRET_NAME" "$SECRET_VALUE" "$PROJECT_ID"
}

# Format project name for resource-specific secrets
FORMATTED_PROJECT_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
DB_NAME="${FORMATTED_PROJECT_NAME}_db"
DB_USER="${FORMATTED_PROJECT_NAME}_user"
DEFAULT_ADMIN_ACCOUNT="${FORMATTED_PROJECT_NAME}_admin"

# Upload the variables to the specified environment
echo "Uploading variables to $ENVIRONMENT_TYPE environment..."

# Create randomly generated secrets
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_DB_PASS" true "$PROJECT_ID"
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_SECRET_KEY" true "$PROJECT_ID"
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_DEFAULT_ADMIN_PASSWORD" true "$PROJECT_ID"
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_ENCRYPTION_KEY" true "$PROJECT_ID"
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_SECURITY_PASSWORD_SALT" true "$PROJECT_ID"

# Create resource-specific secrets with predefined values
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_DB_NAME" false "$PROJECT_ID" "$DB_NAME"
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_DB_USER" false "$PROJECT_ID" "$DB_USER"
create_secret_if_not_exists "${ENVIRONMENT_TYPE}_DEFAULT_ADMIN_ACCOUNT" false "$PROJECT_ID" "$DEFAULT_ADMIN_ACCOUNT"

echo "Variables successfully uploaded to the $ENVIRONMENT_TYPE environment of project $PROJECT_NAME."