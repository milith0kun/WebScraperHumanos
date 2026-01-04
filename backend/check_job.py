import requests
import time
import json

job_id = "69575e1b8d4adb9c9a01b13c"
url = f"http://127.0.0.1:8001/api/v1/scraper/jobs/{job_id}"

print(f"Verificando job {job_id}...")
time.sleep(5)  # Esperar un poco

try:
    response = requests.get(url)
    data = response.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")
