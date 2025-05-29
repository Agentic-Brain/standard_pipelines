"""
OAuth model discovery system.

This module provides automatic discovery of OAuth credential models
by scanning the api directory for models that inherit from OAuthCredentialMixin.
"""
import os
import importlib
import pkgutil
from pathlib import Path
from typing import List, Type
from flask import current_app

from standard_pipelines.api.oauth_system import OAuthCredentialMixin, _oauth_registry


def discover_oauth_models(base_path: str = None) -> List[Type[OAuthCredentialMixin]]:
    """
    Discover all OAuth credential models by scanning the api directory.
    
    This function imports all modules in the api directory, which triggers
    the metaclass registration of any OAuth credential models.
    
    Args:
        base_path: Base path to scan. Defaults to the api directory.
        
    Returns:
        List of discovered OAuth credential model classes.
    """
    discovered_models = []
    
    if base_path is None:
        # Get the api directory path
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Get the package name from the base path
    package_name = 'standard_pipelines.api'
    
    try:
        # Walk through all modules in the api directory
        for finder, module_name, ispkg in pkgutil.walk_packages(
            path=[base_path],
            prefix=f"{package_name}.",
            onerror=lambda x: None
        ):
            # Skip test modules and private modules
            if 'test' in module_name or '__pycache__' in module_name:
                continue
            
            # Only import model modules
            if module_name.endswith('.models') or module_name.endswith('.models_new'):
                try:
                    # Import the module - this triggers metaclass registration
                    importlib.import_module(module_name)
                    if current_app:
                        current_app.logger.debug(f"Successfully imported {module_name}")
                except Exception as e:
                    if current_app:
                        current_app.logger.warning(f"Could not import {module_name}: {e}")
    
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Error during OAuth model discovery: {e}")
    
    # Return all registered models
    return list(_oauth_registry.values())


def ensure_oauth_models_loaded():
    """
    Ensure all OAuth models are loaded by discovering them.
    This should be called during app initialization.
    """
    # Try to discover models
    models = discover_oauth_models()
    
    if current_app:
        current_app.logger.info(f"Discovered {len(models)} OAuth credential models")
        for model in models:
            config = model.get_oauth_config()
            if config:
                current_app.logger.info(f"  - {config.display_name} ({config.name})")
    
    return models