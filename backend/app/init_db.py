from app.audit_log import init_db

if __name__ == "__main__":
    init_db()
    print("Audit log table created successfully.")
