import re

# Read the file
with open(r'c:\Users\Shane Holmes\CascadeProjects\windsurf-project\soleco\backend\app\routers\solana.py', 'r') as file:
    content = file.read()

# Replace the tags
content = content.replace('tags=["Network Status"]', 'tags=["Soleco"]')

# Write the file back
with open(r'c:\Users\Shane Holmes\CascadeProjects\windsurf-project\soleco\backend\app\routers\solana.py', 'w') as file:
    file.write(content)

print("File updated successfully")
