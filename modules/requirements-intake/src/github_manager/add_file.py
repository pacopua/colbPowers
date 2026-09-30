from github import Auth
from github import Github

import argparse

from dotenv import load_dotenv
import json
from loguru import logger
import os
import time



load_dotenv()
ACCESS_TOKEN = os.getenv("GITHUB_TOKEN")

def upload_file_to_repo(folder: str | None, file_name: str | None, content: str, repo_name: str, branch: str = "main", progress_callback=None):
    """
    Uploads a file to a GitHub repository. Appends a timestamp to the filename to avoid collisions.
    
    Args:
        folder (str | None): The folder path in the repo.
        file_name (str | None): The name of the file. If None, uses a timestamp.
        content (str): The file content.
        repo_name (str): The repository name (owner/repo).
        branch (str): The branch to upload to.
        progress_callback (callable, optional): Unused in this implementation but kept for interface consistency.
        
    Returns:
        tuple: (success (bool), file_url (str | None))
    """
    if not ACCESS_TOKEN:
        logger.error("GITHUB_TOKEN not found in environment variables.")
        return False, None

    try:
        auth = Auth.Token(ACCESS_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)

        timestamp = int(time.time())
        if file_name is None:
            final_name = f"{timestamp}.md"
        else:
            final_name = f"{timestamp}_{file_name}"

        if folder:
            # Ensure no double slashes if folder ends with /
            clean_folder = folder.rstrip('/')
            path = f"{clean_folder}/{final_name}"
        else:
            path = final_name

        commit = repo.create_file(
            path=path, 
            message=f"Added {final_name}", 
            content=content, 
            branch=branch
        )

        file_url = commit['content'].html_url
        logger.info(f"Successfully created file at {file_url}")
        
        return True, file_url
    except Exception as e:
        logger.error(f"GitHub Error: {e}")
        return False, None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a file to GitHub.")
    parser.add_argument("file_path", type=str, help="Path to the local file to upload.")
    parser.add_argument("--repo", "-r", type=str, required=True, help="Target repository (owner/name).")
    parser.add_argument("--folder", "-f", type=str, default=None, help="Target folder in the repository.")
    parser.add_argument("--name", "-n", type=str, default=None, help="Target file name in the repository (optional).")
    parser.add_argument("--branch", "-b", type=str, default="main", help="Target branch.")

    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        exit(1)

    with open(args.file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Use provided name or default to the local filename
    target_name = args.name if args.name else os.path.basename(args.file_path)

    logger.info(f"Uploading {args.file_path} to {args.repo}...")
    
    success, url = upload_file_to_repo(
        folder=args.folder, 
        file_name=target_name, 
        content=content, 
        repo_name=args.repo, 
        branch=args.branch
    )

    if success:
        logger.info(f"File uploaded successfully! URL: {url}")
    else:
        logger.error("Failed to upload file.")