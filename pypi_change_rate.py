""" This script monitors the change rates on PyPI (https://pypi.org/simple/) every 60s """
import xmlrpc.client
import time
from datetime import datetime

client = xmlrpc.client.ServerProxy('https://pypi.org/pypi')
last_serial = client.changelog_last_serial()

print(f"[{datetime.now()}] Starting at serial: {last_serial}")

running_avg = 0.0
minute_count = 0
start_time = time.time()

while time.time() - start_time < 3600:
    try:
        time.sleep(60)
        current_serial = client.changelog_last_serial()

        if current_serial > last_serial:
            all_changes = []
            serial = last_serial
            while serial < current_serial:
                # changelog_since_serial(serial) return only 50k changes per query and the returned numbers 
                changes = client.changelog_since_serial(serial)
                if not changes:
                    break
                all_changes.extend(changes)
                serial = changes[-1][-1]

            change_count = len(all_changes)
            unique_packages = {row[0] for row in all_changes}

        else:
            change_count = 0
            unique_packages = set()

        minute_count += 1
        running_avg += (change_count - running_avg) / minute_count

        print(f"[{datetime.now()}]: {change_count} changes, {len(unique_packages)} unique packages | "
              f"Avg: {running_avg:.2f} changes/min")

        last_serial = current_serial

    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}")
