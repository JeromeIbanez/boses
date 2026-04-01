import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.database import SessionLocal


def main():
    db = SessionLocal()
    try:
        result = db.execute(text("DELETE FROM personas"))
        db.commit()
        print(f"Deleted {result.rowcount} persona(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
