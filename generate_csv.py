import os
import csv
import hashlib


mirror_dir = 'pypi_mirror'

HASH_ALGORITHM = "SHA-256"

def digest(to_hash:bytes) -> bytes:
        return hashlib.sha256(to_hash).hexdigest()

def compute_hash_and_length(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        file_hash = digest(data)
        return file_hash, len(data)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None, None


def generate_csv(mirror_dir, output_csv):
    """
    Walks through the mirror directory, computes hashes and lengths for each file, and writes the data to a CSV.
    """
    rows = []

    for root, _, files in os.walk(mirror_dir):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, mirror_dir)
            file_hash, file_length = compute_hash_and_length(file_path)
            
            if file_hash is not None and file_length is not None:
                rows.append({
                    'path': relative_path,
                    'length': file_length,
                    'hash_algorithm': f'{HASH_ALGORITHM}',
                    'hash': file_hash
                })

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['path', 'length', 'hash_algorithm', 'hash']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"CSV generated at {output_csv}")


if __name__ == '__main__':
    output_csv_path = os.path.join(mirror_dir, 'mirror_metadata.csv')
    generate_csv(mirror_dir, output_csv_path)
