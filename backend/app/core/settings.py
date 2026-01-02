import os


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "spatial_asset_manager")
DB_USER = os.getenv("POSTGRES_USER", "sam")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sam_password")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)
