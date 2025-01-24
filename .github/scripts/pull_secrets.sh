#!/bin/bash

# Usage message and argument parsing
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 <project_name> <environment_type> [--print-only|--github-env]"
  exit 1
fi

PROJECT_NAME=$1
ENVIRONMENT_TYPE=$(echo "$2" | tr '[:lower:]' '[:upper:]')

# Default flags/modes
PRINT_ONLY=false
MODE="docker"  # "docker" or "github"

# Parse optional third argument
case "$3" in
  "--print-only")
    PRINT_ONLY=true
    ;;
  "--github-env")
    MODE="github"
    ;;
  ""|*) 
    # No third argument or unrecognized argument => default to Docker secrets
    ;;
esac

# Format project name: lowercase, replace spaces with underscores
FORMATTED_PROJECT_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')

# Fetch project ID from Bitwarden
PROJECT_ID=$(bws project list | jq -r --arg name "$PROJECT_NAME" '.[] | select(.name == $name) | .id')
if [ -z "$PROJECT_ID" ]; then
  echo "Error: Project '$PROJECT_NAME' does not exist in Bitwarden."
  exit 1
fi

# Function to retrieve a secret from Bitwarden and store it based on MODE
store_secret() {
  local SECRET_ID=$1
  local SECRET_KEY=$2

  # Docker secret name: <project>_<secret_key_lower>
  local DOCKER_SECRET_NAME="${FORMATTED_PROJECT_NAME}_$(echo "$SECRET_KEY" | tr '[:upper:]' '[:lower:]')"
  # GitHub environment variable name: use the original SECRET_KEY
  local GITHUB_VAR_NAME="$SECRET_KEY"

  echo "Fetching secret '$SECRET_KEY' from Bitwarden..."

  # Get secret value from Bitwarden
  local SECRET_VALUE
  SECRET_VALUE=$(bws secret get "$SECRET_ID" | jq -r '.value')

  if [ -z "$SECRET_VALUE" ] || [ "$SECRET_VALUE" = "null" ]; then
    echo "Error: Could not fetch a valid value for secret '$SECRET_KEY'"
    return 1
  fi

  if [ "$PRINT_ONLY" = true ]; then
    # Just print the info
    echo "Secret Key:     $SECRET_KEY"
    echo "Value:          $SECRET_VALUE"
    echo "Storage Target: $MODE"
    echo "--------------------------------"
  else
    # If in GitHub mode, store secrets in the GitHub environment file
    if [ "$MODE" = "github" ]; then
      # Check if GITHUB_ENV is defined (in GitHub Actions it is)
      if [ -n "$GITHUB_ENV" ]; then
        echo "$GITHUB_VAR_NAME=$SECRET_VALUE" >> "$GITHUB_ENV"
        echo "Appended $GITHUB_VAR_NAME to \$GITHUB_ENV"
      else
        # Fallback: local shell export (won't persist across steps, but let's handle gracefully)
        export "$GITHUB_VAR_NAME"="$SECRET_VALUE"
        echo "Warning: \$GITHUB_ENV not found. Exported locally: $GITHUB_VAR_NAME"
      fi

    else
      # Docker swarm mode
      # Ensure Swarm is active only once (outside this function is typical, but let's do a check here)
      if ! docker info | grep -q "Swarm: active"; then
        echo "Docker swarm is not initialized. Initializing swarm mode..."
        docker swarm init >/dev/null 2>&1 || {
          echo "Failed to initialize Docker swarm."
          return 1
        }
      fi

      # If secret already exists, remove it first
      if docker secret inspect "$DOCKER_SECRET_NAME" >/dev/null 2>&1; then
        echo "Docker secret '$DOCKER_SECRET_NAME' already exists. Removing..."
        docker secret rm "$DOCKER_SECRET_NAME" >/dev/null 2>&1
      fi

      # Create the Docker secret
      echo "$SECRET_VALUE" | docker secret create "$DOCKER_SECRET_NAME" -
      if [ $? -eq 0 ]; then
        echo "Successfully created Docker secret: '$DOCKER_SECRET_NAME'"
      else
        echo "Failed to create Docker secret: '$DOCKER_SECRET_NAME'"
        return 1
      fi
    fi
  fi
}

# Main execution flow -----------------------------------

# Fetch all secrets for the project that match the environment type
echo "Fetching secrets for '$ENVIRONMENT_TYPE' environment..."
SECRETS_LIST=$(bws secret list "$PROJECT_ID")
if [ $? -ne 0 ]; then
  echo "Error: Failed to fetch secrets list from Bitwarden."
  exit 1
fi

# Filter secrets by environment prefix (e.g., 'DEV_', 'TESTING_', 'PROD_')
SECRETS_JSON=$(echo "$SECRETS_LIST" | jq -r --arg env "$ENVIRONMENT_TYPE" '
  [.[] | select(.key | startswith($env))]
')

if [ $? -ne 0 ]; then
  echo "Error: Failed to parse secrets with jq."
  echo "Debug: Secrets list structure:"
  echo "$SECRETS_LIST" | jq '.'
  exit 1
fi

if [ "$SECRETS_JSON" == "[]" ]; then
  echo "No secrets found for environment '$ENVIRONMENT_TYPE'."
  echo "  (Expected secret keys to start with '${ENVIRONMENT_TYPE}_')"
  exit 1
fi

# Process each secret
echo "Pulling secrets from Bitwarden..."
echo "$SECRETS_JSON" | jq -r '.[] | "\(.id)|\(.key)"' | while IFS='|' read -r SECRET_ID SECRET_KEY; do
  store_secret "$SECRET_ID" "$SECRET_KEY" || {
    echo "Warning: Error processing secret '$SECRET_KEY'. Continuing..."
  }
done

# Summaries based on mode
if [ "$PRINT_ONLY" = true ]; then
  echo -e "\nOperation complete in print-only mode."
elif [ "$MODE" = "docker" ]; then
  echo -e "\nSuccessfully processed secrets in Docker Swarm mode."
  echo "Listing Docker secrets with prefix '${FORMATTED_PROJECT_NAME}_':"
  docker secret ls | grep "${FORMATTED_PROJECT_NAME}_"
elif [ "$MODE" = "github" ]; then
  echo -e "\nSuccessfully processed secrets in GitHub environment mode."
  echo "Secrets have been appended to the GitHub Actions environment (\$GITHUB_ENV)."
fi
