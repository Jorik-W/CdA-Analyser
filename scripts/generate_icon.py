# generate_icon.py
import base64

# Read the .ico file and encode it
with open('logo_blue.ico', 'rb') as f:
    icon_data = f.read()

# Encode as base64
b64_data = base64.b64encode(icon_data).decode('utf-8')

# Write to icon.py
with open('icon.py', 'w') as f:
    f.write(f'LOGO_BASE64 = """{b64_data}"""\n')

print("icon.py generated successfully!")