# Issue Organizer

This module provides functionality to organize and manage issues within Azure Blob Storage. It creates a hierarchical structure of Clients, Projects, Iterations, and Issues.

## Features

- **Hierarchical Organization**: Manages a directory structure: `Client / Project / Iteration / IssueID`.
- **Issue Management**: Creates issues as folders containing an `issue_details.json` file.
- **Azure Blob Storage Integration**: Uses `azure-storage-blob` (via a custom backend wrapper) to persist data.
- **Listing Capabilities**: Provides methods to list clients, projects, iterations, and issues.

## Installation

Ensure you have the required dependencies installed. This module relies on `fsspec`, `adlfs`, and `azure-storage-blob`.

```bash
pip install fsspec adlfs azure-storage-blob
```

## Configuration

The module requires an Azure Storage connection string. Set the following environment variable:

```bash
export AZURE_STORAGE_CONNECTION_STRING="your_connection_string_here"
```

## Usage

### Initialization

```python
import os
from issue_organizer.organizador import AzureOrganizer
from issue_organizer.azure_storage_manger.storage_manager import StorageManager
from issue_organizer.azure_storage_manger.backends.azure import AzureStorageBackend, AzureBackendConfig

# 1. Configure the backend
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = "my-issue-container"

config = AzureBackendConfig(
    protocol="az",
    connection_string=connection_string,
    create_parent_dirs=True
)

# 2. Initialize Backend and Storage Manager
backend = AzureStorageBackend(config)
storage_client = StorageManager(backend, base_uri=f"az://{container_name}")

# 3. Initialize Organizer
organizer = AzureOrganizer(storage_client)
```

### Creating Structure

```python
client = "MyClient"
project = "WebRedesign"
iteration = "Sprint1"
issue_data = {
    "id": "ISSUE-001",
    "title": "Fix login bug",
    "description": "Login fails with 500 error",
    "priority": "High"
}

# Create the hierarchy
organizer.create_client(client)
organizer.create_project(client, project)
organizer.create_iteration(client, project, iteration)

# Create an issue (creates a folder 'ISSUE-001' with 'issue_details.json' inside)
organizer.create_issue(client, project, iteration, issue_data)
```

### Listing Items

```python
clients = organizer.list_clients()
projects = organizer.list_projects(client)
iterations = organizer.list_iterations(client, project)
issues = organizer.list_issues(client, project, iteration)
```

## Structure on Azure Blob Storage

The resulting structure in your container will look like this:

```text
my-issue-container/
└── MyClient/
    └── WebRedesign/
        └── Sprint1/
            └── ISSUE-001/
                └── issue_details.json
```
