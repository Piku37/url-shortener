from app import app
import os
print("SQLALCHEMY_DATABASE_URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
print("Current working dir:", os.getcwd())
print("Files in /app:", os.listdir("/app"))
print("Does /app/data exist?:", os.path.exists("/app/data"))
try:
    print("Files in /app/data:", os.listdir("/app/data"))
except Exception as e:
    print("Cannot list /app/data:", e)
