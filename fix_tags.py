# Simple script to replace Network Status tags with Soleco tags
file_path = r'c:\Users\Shane Holmes\CascadeProjects\windsurf-project\soleco\backend\app\routers\solana.py'

with open(file_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Replace Network Status tags with Soleco tags
content = content.replace('tags=["Network Status"]', 'tags=["Soleco"]')

with open(file_path, 'w', encoding='utf-8') as file:
    file.write(content)

print("Tags updated successfully!")
