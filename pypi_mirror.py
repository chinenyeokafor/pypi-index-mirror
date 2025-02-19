import os
import requests
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
import xmlrpc.client
import shutil
from generate_csv import generate_updated_csv
from rstuf import send_add_requests, send_remove_requests

base_url = "https://pypi.org/simple/"
mirror_dir = 'pypi_mirror'
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

def update_root_index(local_index_path, root_index):
    os.makedirs(os.path.dirname(local_index_path), exist_ok=True)
    with open(local_index_path, "w", encoding="utf-8") as f:
        f.write(root_index)

def fetch_package_index(args):
    """download from pypi and save the index for an individual package"""
    base_url, package_name, mirror_dir = args
    package_url = base_url + package_name
    try:
        response = requests.get(package_url)
        response.raise_for_status()

        package_dir = os.path.join(mirror_dir, "simple", package_name)
        os.makedirs(package_dir, exist_ok=True)
        with open(os.path.join(package_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(response.text)
            print(f"Updated {package_name}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching index for {package_name}: {e}")
    except Exception as e:
        print(f"Unexpected error fetching index for {package_name}: {e}")

def get_local_packages():
    """get locally stored packages"""
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


def update_mirror(local_index_path):
    """
    Handles changelog events as follows:
    - 'new', 'add', 'create', 'update', 'docupdate': Downloads/updates the pkg
    - 'remove': Deletes the package dir
    - 'rename': Deletes the old repository, then downloads/updates the renamed pkg
    """
    with open(last_serial_path, 'r') as f:
        serial = int(f.readline().split(":")[1].strip())

    current_serial = client.changelog_last_serial()

    pkgs_to_download, pkgs_to_remove, last_serial = get_changes(serial, current_serial)

    print(f"Removing {len(pkgs_to_remove)}, Adding {len(pkgs_to_download)} pkgs" )

    handle_removals(pkgs_to_remove)
    handle_downloads(pkgs_to_download)
    
    if pkgs_to_download:
        artifacts_metadata = generate_updated_csv(pkgs_to_download)
        send_add_requests(artifacts_metadata)
    
    if pkgs_to_remove:
        removed_artifacts = [ os.path.join("simple", package) for package in pkgs_to_remove]
        send_remove_requests(removed_artifacts)
    
    with open(last_serial_path, 'w') as f:
        f.write(f"Last Serial: {last_serial}")
    
    #update root index
    update_root_index(local_index_path, download_root_index())

def get_changes(serial, current_serial):
    """Process changelog entries and categorize packages by events
        Change events are: 'add', 'create', 'new', 'rename', 'remove', 'update', 'docupdate' """
    packages_to_download = set()
    packages_to_remove = set()

    # nb: changelog_since_serial(serial) returns only 50k changes per query
    while serial < current_serial:
        changes = client.changelog_since_serial(serial)
        if not changes: break

        for change in changes:
            package_name = change[0]
            event = change[3].split(" ")[0] 

            if event in {"new", "add", "create", "update", "docupdate"}:
                packages_to_download.add(package_name)
            elif event == "remove":
                packages_to_remove.add(package_name)
            elif event == "rename":
                old_name = change[3].split("rename from ")[1].strip()
                packages_to_remove.add(old_name)
                packages_to_download.add(package_name)

        serial = changes[-1][-1]

    return packages_to_download, packages_to_remove, serial


def handle_removals(packages):
    """remove packages from the local mirror"""
    for package in packages:
        package_dir = os.path.join(mirror_dir, "simple", package)
        if os.path.exists(package_dir):
            try:
                shutil.rmtree(package_dir)
                print(f"Removed {package}")
            except Exception as e:
                print(f"Error removing {package}: {e}")


def handle_downloads(packages):
    """download packages in the local mirror"""
    if packages:
        print(f"Updating {len(packages)} packages...")
        with Pool(cpu_count()) as pool:
            pool.map(fetch_package_index, [(base_url, p, mirror_dir) for p in packages])
    else:
        print("No new update to add")


def main():
    local_index_path = os.path.join(mirror_dir, "index.html")

    needs_initialization = (
        not os.path.exists(local_index_path)
        or not os.path.exists(last_serial_path)
        # or not are_all_pkgs_downloaded(local_index_path)
    )

    if needs_initialization:
        print("Initializing local mirror...")
        initialize_mirror(local_index_path)
    else:
        print("Updating local mirror...")
        update_mirror(local_index_path)


def initialize_mirror(local_index_path):
    """instantiate a local mirror and download all packages from root simple index"""

    if not os.path.exists(local_index_path):
        serial = client.changelog_last_serial()
        root_index = download_root_index()
        if root_index is None:
            return
        update_root_index(local_index_path, root_index)
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
        print(f"Found {len(tasks_arg):,} packages to update")
        num_workers = min(cpu_count(), len(tasks_arg))
        with Pool(num_workers) as pool:
            pool.map(fetch_package_index, tasks_arg)

        if serial:
            with open(last_serial_path, 'w') as f:
                f.write(f"Last Serial: {serial}")
    else:
        print("No updates required for any packages.")

if __name__ == "__main__":
    main()
