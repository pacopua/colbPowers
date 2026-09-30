import json
import logging
import os
import sys
import tempfile
from loguru import logger
from typing import List, Dict, Any, Optional

file_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(file_path)

from azure_storage_manger.storage_manager import StorageManager
from .models import Client, Project, Instance  # Import the models


class AzureOrganizer:
    """
    This class manages the organization of features in Azure Storage.
    Structure:
    Client
    |-- Projects
    |   |-- Iterations
    |       |-- features
    """
    def __init__(self, storage_manager : StorageManager):
        """
        Initialize with an Azure Storage Client (StorageManager).
        """
        self.storage_manager = storage_manager

    def create_client(self, client_name: str) -> None:
        """Create a client directory."""
        logger.info(f"Creating client directory for: {client_name}")
        self.storage_manager.make_dirs(client_name)
        logger.info(f"Created client: {client_name}")

    def create_project(self, client_name: str, project_name: str) -> None:
        """Create a project directory under a client."""
        path = f"{client_name}/{project_name}"
        self.storage_manager.make_dirs(path)
        logger.info(f"Created project: {path}")

    def create_iteration(self, client_name: str, project_name: str, iteration_name: str) -> None:
        """Create an iteration directory under a project."""
        path = f"{client_name}/{project_name}/{iteration_name}"

        self.storage_manager.make_dirs(path)
        logger.info(f"Created iteration: {path}")

    def create_feature(self, client_name: str, project_name: str, iteration_name: str, feature_data: Dict[str, Any]) -> None:
        """
        Create an feature folder under an iteration and save details.
        """
        feature_id = feature_data.get('id', 'unknown_feature')
        
        # Create feature directory
        feature_path = f"{client_name}/{project_name}/{iteration_name}/{feature_id}"
        self.storage_manager.make_dirs(feature_path)
        
        # Save feature details
        filename = "feature_details.json"
        remote_path = f"{feature_path}/{filename}"
        
        # Use mkstemp to avoid features with NamedTemporaryFile on some platforms/configurations
        fd, tmp_path = tempfile.mkstemp(suffix='.json')
        try:
            with os.fdopen(fd, 'w') as tmp:
                json.dump(feature_data, tmp, indent=2)
            
            # Verify file exists before upload
            if not os.path.exists(tmp_path):
                raise FileNotFoundError(f"Temporary file creation failed: {tmp_path}")
                
            self.storage_manager.upload_file(tmp_path, remote_path)
            logger.info(f"Created feature: {remote_path}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def list_clients(self) -> List[str]:
        """List all clients (top level directories)."""
        clients = self.storage_manager.list_files()
        # we take only the basenames
        return [os.path.basename(client) for client in clients]

    def list_projects(self, client_name: str) -> List[str]:
        """List projects for a client."""
        projects = self.storage_manager.list_path(client_name)
        return [os.path.basename(project) for project in projects]

    def list_iterations(self, client_name: str, project_name: str) -> List[str]:
        """List iterations for a project."""
        path = f"{client_name}/{project_name}"
        iterations = self.storage_manager.list_path(path)
        return [os.path.basename(iteration) for iteration in iterations]

    def list_features(self, client_name: str, project_name: str, iteration_name: str) -> List[str]:
        """List features for an iteration."""
        path = f"{client_name}/{project_name}/{iteration_name}"
        return self.storage_manager.list_path(path)

    def get_blob_url(self, path: str) -> str:
        """Get the full URL for a blob."""
        return self.storage_manager._full(path)

    def organize_features(self, features: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Organize a list of features by project and iteration.
        Returns: {project: {iteration: [features]}}
        """
        organized_features = {}
        for feature in features:
            project = feature.get('project', 'Unassigned')
            iteration = feature.get('iteration', 'Backlog')
            
            if project not in organized_features:
                organized_features[project] = {}
            
            if iteration not in organized_features[project]:
                organized_features[project][iteration] = []
                
            organized_features[project][iteration].append(feature)
            
        return organized_features