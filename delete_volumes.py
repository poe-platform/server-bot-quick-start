import json
import subprocess
import time
from datetime import datetime, timezone

result = subprocess.run(
    ["modal", "nfs", "list", "--json"], capture_output=True, text=True
)

for volume in json.loads(result.stdout):
    if not volume["Name"].startswith("vol-u-"):
        continue
    dt = datetime.strptime(volume["Created at"], "%Y-%m-%d %H:%M:%S.%f%z")
    dt_utc = dt.astimezone(timezone.utc)
    created_time = (dt_utc - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()

    if int(time.time()) - created_time > 24 * 60 * 60:
        # you can only delete individual files, but not the nfs
        print(volume)
