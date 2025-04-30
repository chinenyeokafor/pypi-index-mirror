# PyPI Mirror Update

This project helps maintain a local mirror of packages from PyPI, which is then synchronized with RSTUF following the [Repository Service for TUF Guide](https://repository-service-tuf.readthedocs.io/en/stable/guide/general/usage.html). The process involves an initial synchronization of the mirror, followed by the generation of a CSV file that is used for the initial RSTUF bootstrapping. The generated CSV contains metadata about the packages in the PyPI mirror directory, such as the relative path, length, hash algorithm, and hash.

## Initial Bootstrapping

To perform the initial bootstrapping, follow these steps:

1. **Mirror the Index Locally**:
   Run the following command to mirror the PyPI index locally:
   ```sh
   python pypi_mirror.py
   ```
   Since this is the first synchronization (i.e., the mirror does not exist locally), this command will create the local mirror with the following structure:

   ```
   ├── pypi-index-mirror
   │   ├── pypi_mirror
   │   │   ├── index.html
   │   │   └── simple
   │   │       ├── <package-name>
   │   │       │   ├── index.html
   ```

   - `index.html` (global, inside `pypi_mirror/`) – Lists all available packages in the mirror.
   - `simple/<package-name>/index.html` – Lists available versions of a specific package.

2. **Generate the CSV for Initial Bootstrapping**:
   Run the following command to generate a CSV file of the local mirror, which will be used for the initial bootstrapping:
   ```sh
   python3 generate_csv.py
   ```

## Subsequent Updates

After the initial bootstrapping, the process involves two main functions: checking for changelog events from PyPI since the last synchronization and updating RSTUF accordingly. It handles changelog events as follows:
- `'new'`, `'add'`, `'create'`, `'update'`, `'docupdate'`: Downloads or updates the package on RSTUF.
- `'remove'`: Deletes the package from RSTUF.
- `'rename'`: Deletes the old package and then downloads or updates the renamed package.

To fetch changes and update the local mirror, follow these steps:

1. **Fetch Changes**:
   Run the following command to check for changelog events, update the local mirror, and send add/remove requests to RSTUF accordingly:
   ```sh
   python pypi_mirror.py
   ```
   If the local mirror already exists, the script will assume it is an update and will check for changelog events, update the local mirror, and send appropriate requests to RSTUF