import os

folders = [
    "app/templates/auth",
    "app/templates/user",
    "app/templates/admin",
    "app/static/css",
    "app/static/js",
]

files = [
    "app/_init_.py",
    "app/models.py",
    "app/routes.py",
    "app/tatum.py",
    "run.py",
]

# Create folders
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"Created folder: {folder}")

# Create files
for file in files:
    with open(file, "w") as f:
        pass
    print(f"Created file: {file}")

print("\n✅ Vault project structure created successfully!")