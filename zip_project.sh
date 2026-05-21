#!/bin/bash
# zip_project.sh
# Zips the current project into CN334-project.zip inside the parent folder of the project, excluding unwanted files.

# Go to the script's directory
cd "$(dirname "$0")"

# Remove any existing zip file
rm -f ../CN334-project.zip

echo "Creating CN334-project.zip..."

# Zip the contents of the current directory, excluding specified directories and files.
# -r means recursive.
# -x specifies exclusions.
zip -r ../CN334-project.zip . \
  -x "*.sqlite3" \
  -x "*/*.sqlite3" \
  -x "*/*/*.sqlite3" \
  -x "*/*/*/*.sqlite3" \
  -x ".env" \
  -x "*/.env" \
  -x "*/*/.env" \
  -x "*/*/*/.env" \
  -x "*.pyc" \
  -x "*/*.pyc" \
  -x "*/*/*.pyc" \
  -x "*/*/*/*.pyc" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x "*/*/__pycache__/*" \
  -x "*/*/*/__pycache__/*" \
  -x "venv/*" \
  -x "*/venv/*" \
  -x ".venv/*" \
  -x "*/.venv/*" \
  -x ".DS_Store" \
  -x "*/.DS_Store" \
  -x "*/*/.DS_Store" \
  -x "*/*/*/.DS_Store" \
  -x ".git/*" \
  -x "*/.git/*" \
  -x ".vscode/*" \
  -x "*/.vscode/*" \
  -x ".idea/*" \
  -x "*/.idea/*" \
  -x "zip_project.sh"

echo "ZIP file created successfully: ../CN334-project.zip"
chmod 644 ../CN334-project.zip
