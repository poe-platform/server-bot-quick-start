import os
import zipfile

import requests

# URL of the repository
repo_url = "https://github.com/poe-platform/documentation/archive/refs/heads/main.zip"

# Download the ZIP file
response = requests.get(repo_url)
zip_file_path = "documentation.zip"

with open(zip_file_path, "wb") as file:
    file.write(response.content)

# Create a directory to store the extracted files
extracted_dir = "files_HelpDeskDemo"
os.makedirs(extracted_dir, exist_ok=True)

# Extract all .md files to the root directory
with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
    for file in zip_ref.namelist():
        if file.endswith(".md"):
            zip_ref.extract(file, extracted_dir)

# Move all .md files to the root directory
for root, _, files in os.walk(extracted_dir):
    for file in files:
        if file.endswith(".md"):
            file_path = os.path.join(root, file)
            new_file_path = os.path.join(extracted_dir, file)
            os.rename(file_path, new_file_path)

# Print the paths of the extracted .md files
for file in os.listdir(extracted_dir):
    if file.endswith(".md"):
        file_path = os.path.join(extracted_dir, file)
        print(file_path)

# Clean up the downloaded ZIP file
os.remove(zip_file_path)


article_urls = [
    "https://poe.com/about",
    "https://help.poe.com/hc/en-us/articles/19944206309524-Poe-FAQs",
    "https://help.poe.com/hc/en-us/articles/19945140063636-Poe-Subscriptions-FAQs",
    "https://poe.com/tos",
    "https://poe.com/privacy",
    "https://poe.com/api_terms",
]

for _ in article_urls:
    # TODO: (automatically download these files and save as markdown)
    pass
