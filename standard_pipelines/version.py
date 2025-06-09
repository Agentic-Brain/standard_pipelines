# Base framework version using semantic versioning (MAJOR.MINOR.PATCH)
FLASK_BASE_VERSION = "0.2.1"

# Application version - always 0.0.0 in base framework
# Will be updated in derived projects
__version__ = "1.4.3"

def get_versions():
    return {
        "flask_base": FLASK_BASE_VERSION,
        "app": __version__
    } 
