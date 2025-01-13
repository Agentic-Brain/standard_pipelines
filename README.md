## Flask Base
This is the base structure for a new flask project. It will be updated overtime as more things are added to the standard flask setup

## Modifications
Below are the modifications you will need to make to update this to a new project

### .flaskenv
- Change FLASK_APP= to name of your new application

## docker-compose-dev.yaml
- Change all references to flask-base to application name
## .env
- openssl rand -base64 32