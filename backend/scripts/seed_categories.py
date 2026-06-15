from app.database import SessionLocal
from app.models.category import Category

CATEGORIES = [
    {"code": "food_dining", "name_en": "Food and Dining", "name_th": "อาหารและเครื่องดื่ม"},
    {"code": "groceries", "name_en": "Groceries", "name_th": "ของชำ"},
    {"code": "transportation", "name_en": "Transportation", "name_th": "การเดินทาง"},
    {"code": "utilities", "name_en": "Utilities", "name_th": "ค่าสาธารณูปโภค"},
    {"code": "shopping", "name_en": "Shopping", "name_th": "ช้อปปิ้ง"},
    {"code": "healthcare", "name_en": "Healthcare", "name_th": "สุขภาพ"},
    {"code": "education", "name_en": "Education", "name_th": "การศึกษา"},
    {"code": "entertainment", "name_en": "Entertainment", "name_th": "ความบันเทิง"},
    {"code": "travel", "name_en": "Travel", "name_th": "การท่องเที่ยว"},
    {"code": "personal_care", "name_en": "Personal Care", "name_th": "ของใช้ส่วนตัว"},
    {"code": "business", "name_en": "Business", "name_th": "ธุรกิจ"},
    {"code": "other", "name_en": "Other", "name_th": "อื่นๆ"}
]

def seed_categories():
    db = SessionLocal()
    inserted = 0
    updated_restored = 0
    skipped = 0
    try:
        for cat_data in CATEGORIES:
            # Query for the category, regardless of soft delete
            category = db.query(Category).filter(Category.code == cat_data["code"]).first()
            if category:
                needs_update = False
                if category.deleted_at is not None:
                    category.deleted_at = None
                    needs_update = True
                if category.name_en != cat_data["name_en"] or category.name_th != cat_data["name_th"]:
                    category.name_en = cat_data["name_en"]
                    category.name_th = cat_data["name_th"]
                    needs_update = True
                
                if needs_update:
                    updated_restored += 1
                else:
                    skipped += 1
            else:
                new_cat = Category(
                    code=cat_data["code"],
                    name_en=cat_data["name_en"],
                    name_th=cat_data["name_th"],
                    is_active=True
                )
                db.add(new_cat)
                inserted += 1
        db.commit()
        print(f"Categories seed completed:")
        print(f"  Inserted: {inserted}")
        print(f"  Updated/Restored: {updated_restored}")
        print(f"  Skipped: {skipped}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding categories: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_categories()
