import os
import csv
import hashlib


mirror_dir = 'pypi_mirror'

HASH_ALGORITHM = "blake2b"
HASH_LENGTH = 32

def digest(to_hash:bytes) -> bytes:
        return hashlib.blake2b(to_hash, digest_size=HASH_LENGTH).hexdigest()

def hash_algorithm_str() -> str:
    return f"{HASH_ALGORITHM}-{HASH_LENGTH}"

def compute_hash_and_length(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        file_hash = digest(data)
        return file_hash, len(data)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None, None


def generate_all_csv(mirror_dir, output_csv):
    """
    Walks through the mirror directory, computes hashes and lengths for each file, and writes the data to a CSV.
    """
    rows = []

    simple_dir = os.path.join(mirror_dir, 'simple')
    updated_pkg = [pkg for pkg in os.listdir(simple_dir) if os.path.isdir(os.path.join(simple_dir, pkg))]
    rows = generate_updated_csv(updated_pkg)

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['path', 'length', 'hash_algorithm', 'hash']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"CSV generated at {output_csv}")


def generate_updated_csv(updated_pkg):
    """
    Computes hashes and lengths for updated packages
    """
    # simple/index.html is always updated
    updated_pkg.add('') #root simple directory

    rows = []

    for pkg_name in updated_pkg:
        pkg_dir = os.path.join(mirror_dir, 'simple', pkg_name) if pkg_name else mirror_dir
        file_hash, file_length = compute_hash_and_length(os.path.join(pkg_dir, 'index.html'))
        relative_path = os.path.relpath(pkg_dir, mirror_dir)
            
        if file_hash is not None and file_length is not None:
            rows.append({
                'path': relative_path,
                'length': file_length,
                'hash_algorithm': hash_algorithm_str(),
                'hash': file_hash
            })
    return rows


if __name__ == '__main__':
    output_csv_path = os.path.join(mirror_dir, 'mirror_metadata.csv')
    generate_all_csv(mirror_dir, output_csv_path)
