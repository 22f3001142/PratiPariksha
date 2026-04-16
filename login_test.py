import requests
resp = requests.post('http://127.0.0.1:5000/api/auth/login', json={'role':'admin','username':'admin','password':'admin123'})
print(resp.status_code, resp.text)
