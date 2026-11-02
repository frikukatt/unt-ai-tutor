
from app.database import SessionLocal
from app.models import SkillProfile


def main():
    db = SessionLocal()

    try:
        profiles = db.query(SkillProfile).all()
        updated = 0

        for profile in profiles:
            if profile.max_points > 0:
                profile.accuracy = round(
                    profile.total_points
                    / profile.max_points
                    * 100,
                    2,
                )
            else:
                profile.accuracy = 0

            updated += 1

        db.commit()

        print("Пересчёт завершён.")
        print(f"Обновлено профилей: {updated}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
