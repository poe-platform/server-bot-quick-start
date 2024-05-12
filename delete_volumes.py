import json
import subprocess

command = "modal app list --json > app.json"
subprocess.run(command, shell=True, capture_output=True, text=True)

with open("app.json") as f:
    srr = f.read()

for opp in json.loads(srr):
    if opp["Name"].startswith("vol-u-"):
        print(opp["Name"])
        print(opp["State"])
        command = f"modal app stop {opp['App ID']}"
        subprocess.run(command, shell=True, capture_output=True, text=True)
