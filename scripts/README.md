# Database Helper Scripts

This directory contains utility scripts for database management, seeding, and maintenance.

## Safety First
Many scripts here are **destructive** (e.g., they drop tables or reset the database). 
- Destructive Python scripts are protected by the `@require_dev_only` decorator in `scripts/utils.py`.
- They will refuse to run if the environment variable `ENVIRONMENT` is set to `production`.
- Shell scripts like `reset.sh` will prompt for confirmation if they detect a production environment.

## Usage

Always run these scripts using `uv run python` from the project root.

### Seeding and Reseting
- **`reseed_all.sh`**: Robust shell script that drops the schema, runs migrations, and seeds data. **(Supports Dev & Prod)**
- **`seed_data.py`**: Python script called by `reseed_all.sh` to populate data from `data/*.csv`.
- **`reseed_dashboard.py`**: Seeds specific data for the admin dashboard. **(Dev only)**
- **`reset.sh`**: Legacy shell script that drops the database at the PostgreSQL level.

### User Management
- **`create_user.py`**: Create a new user with a specific role.
  ```bash
  uv run python scripts/create_user.py --email user@example.com --password securepass --role admin
  ```
- **`dump_users.py`**: Lists all users currently in the database.
  ```bash
  uv run python scripts/dump_users.py
  ```

### Mock Data Generation
- **`generate_mock_data.py`**: Generates synthetic CSV data for students, activities, etc.
- **`generate_dashboard_mock_data.py`**: Generates synthetic CSV data specifically for dashboard scenarios.

## Development Environment
The scripts automatically detect your environment based on the `ENVIRONMENT` variable (defaults to `development`). Ensure your `.env` file is correctly configured.
