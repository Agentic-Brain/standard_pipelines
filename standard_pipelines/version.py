# Base framework version using semantic versioning (MAJOR.MINOR.PATCH)
FLASK_BASE_VERSION = "0.2.1"

# Application version - always 0.0.0 in base framework
# Will be updated in derived projects
APP_VERSION = "1.0.0"

def get_versions():
    return {
        "flask_base": FLASK_BASE_VERSION,
        "app": APP_VERSION
    } 
