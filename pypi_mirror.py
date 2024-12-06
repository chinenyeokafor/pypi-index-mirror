import os
import requests
import hashlib
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
import xmlrpc

base_url = "https://pypi.org/simple/"
mirror_dir = '/content/pypi_mirror'
last_serial_path = os.path.join(mirror_dir, "last_serial.txt")
client = xmlrpc.client.ServerProxy('https://pypi.org/pypi')

def download_root_index():
    """get the root simple index from pypi"""
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException:
        print("Failed to fetch the PyPI simple index.")
        return None

def fetch_package_index(args):
    """fetch and save the index for an individual package"""
    base_url, package_name, mirror_dir = args
    package_url = base_url + package_name
    try:
        response = requests.get(package_url)
        response.raise_for_status()

        package_dir = os.path.join(mirror_dir, "simple", package_name)
        os.makedirs(package_dir, exist_ok=True)
        with open(os.path.join(package_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching index for {package_name}: {e}")
    except Exception as e:
        print(f"Unexpected error fetching index for {package_name}: {e}")

def get_local_packages():
    """get a set of locally stored packages"""
    simple_dir = os.path.join(mirror_dir, "simple")
    return set(os.listdir(simple_dir)) if os.path.exists(simple_dir) else set()


def are_all_pkgs_downloaded(local_index_path):
    """check if all packages in the root simple index are downloaded"""
    simple_dir = os.path.join(mirror_dir, "simple")
    if not os.path.exists(local_index_path) or not os.path.exists(simple_dir):
        return False

    with open(local_index_path, 'r', encoding='utf-8') as file:
        packages_to_download = {a['href'] for a in BeautifulSoup(file, 'html.parser').find_all('a', href=True)}

    local_packages = {entry.name for entry in os.scandir(simple_dir) if entry.is_dir()}
    return packages_to_download == local_packages


def update_mirror():
    """update local mirror with recent events from pypi"""
    with open(last_serial_path, 'r') as f:
        serial = int(f.readline().split(":")[1].strip())

    packages, current_serial = set(), client.changelog_last_serial()
    # changelog_since_serial(serial) return only 50k changes per query and the returned numbers 
    while serial < current_serial:
        changes = client.changelog_since_serial(serial)
        if not changes: break
        packages.update(row[0] for row in changes)
        serial = changes[-1][-1]

    if packages:
        print(f"Updating {len(packages)} packages...")
        with Pool(cpu_count()) as pool:
            pool.map(fetch_package_index, [(base_url, p, mirror_dir) for p in packages])
        with open(last_serial_path, 'w') as f:
            f.write(f"Last Serial: {serial}")
    else:
        print("No new changes to update.")

def main():
    local_index_path = os.path.join(mirror_dir, "index.html")

    needs_initialization = (
        not os.path.exists(local_index_path)
        or not os.path.exists(last_serial_path)
        or not are_all_pkgs_downloaded(local_index_path)
    )

    if needs_initialization:
        print("Initializing local mirror...")
        initialize_mirror(local_index_path)
    else:
        print("Updating local mirror...")
        update_mirror()


def initialize_mirror(local_index_path):
    """instantiate a local mirror and download all packages from root simple index"""

    if not os.path.exists(local_index_path):
        serial = client.changelog_last_serial()
        root_index = download_root_index()
        if root_index is None:
            return
        os.makedirs(os.path.dirname(local_index_path), exist_ok=True)
        with open(local_index_path, "w", encoding="utf-8") as f:
            f.write(root_index)
    else:
        serial = None
        with open(local_index_path, "r", encoding="utf-8") as f:
            root_index = f.read()

    soup = BeautifulSoup(root_index, "html.parser")
    package_names = {link.text.strip() for link in soup.find_all('a')} 

    local_pkgs = get_local_packages()

    # process only pending packages
    new_packages = package_names - local_pkgs
    tasks_arg = [(base_url, package, mirror_dir) for package in new_packages]

    if tasks_arg:
        print(f"Found {len(tasks_arg)} packages to update")
        num_workers = min(cpu_count(), len(tasks_arg))
        with Pool(num_workers) as pool:
            pool.map(fetch_package_index, tasks_arg)

        # save the last serial if set
        if serial:
            with open(last_serial_path, 'w') as f:
                f.write(f"Last Serial: {serial}")
    else:
        print("No updates required for any packages.")

if __name__ == "__main__":
    main()
