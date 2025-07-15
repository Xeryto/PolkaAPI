#!/usr/bin/env python3
"""
Script to populate the database with sample brands and styles data
"""
from database import SessionLocal, init_db
from models import Brand, Style
from sqlalchemy.orm import Session

# Sample brands data
BRANDS_DATA = [
    {"id": 1, "name": "Армани", "slug": "armani", "description": "Итальянский дом моды"},
    {"id": 2, "name": "Бурберри", "slug": "burberry", "description": "Британский люксовый бренд"},
    {"id": 3, "name": "Гуччи", "slug": "gucci", "description": "Итальянский модный дом"},
    {"id": 4, "name": "Хьюго Босс", "slug": "hugo-boss", "description": "Немецкий бренд премиум-класса"},
    {"id": 5, "name": "Ральф Лорен", "slug": "ralph-lauren", "description": "Американский бренд классической одежды"},
    {"id": 6, "name": "Версаче", "slug": "versace", "description": "Итальянский дом моды"},
    {"id": 7, "name": "Прада", "slug": "prada", "description": "Итальянский люксовый бренд"},
    {"id": 8, "name": "Кельвин Кляйн", "slug": "calvin-klein", "description": "Американский бренд одежды"},
    {"id": 9, "name": "Балман", "slug": "balmain", "description": "Французский дом моды"},
    {"id": 10, "name": "Фенди", "slug": "fendi", "description": "Итальянский люксовый бренд"},
    {"id": 11, "name": "Том Форд", "slug": "tom-ford", "description": "Американский дизайнер"},
    {"id": 12, "name": "Шанель", "slug": "chanel", "description": "Французский дом моды"}
]

# Sample styles data
STYLES_DATA = [
    {"id": "casual", "name": "Повседневный", "description": "Комфортная одежда для ежедневной носки"},
    {"id": "formal", "name": "Деловой", "description": "Элегантная одежда для офиса и встреч"},
    {"id": "sport", "name": "Спортивный", "description": "Функциональная одежда для активного образа жизни"},
    {"id": "romantic", "name": "Романтичный", "description": "Женственные, изящные силуэты"},
    {"id": "streetwear", "name": "Уличный", "description": "Современный городской стиль"},
    {"id": "vintage", "name": "Винтаж", "description": "Классические силуэты прошлых десятилетий"},
    {"id": "minimalist", "name": "Минимализм", "description": "Простые, лаконичные силуэты и нейтральные цвета"},
    {"id": "bohemian", "name": "Богемный", "description": "Свободные силуэты и этнические мотивы"}
]

def populate_brands(db: Session):
    """Populate brands table with sample data"""
    print("📦 Populating brands...")
    
    for brand_data in BRANDS_DATA:
        # Check if brand already exists
        existing_brand = db.query(Brand).filter(Brand.id == brand_data["id"]).first()
        if existing_brand:
            print(f"  ⚠️  Brand {brand_data['name']} already exists, skipping...")
            continue
        
        brand = Brand(**brand_data)
        db.add(brand)
        print(f"  ✅ Added brand: {brand_data['name']}")
    
    db.commit()
    print(f"✅ Successfully populated {len(BRANDS_DATA)} brands")

def populate_styles(db: Session):
    """Populate styles table with sample data"""
    print("🎨 Populating styles...")
    
    for style_data in STYLES_DATA:
        # Check if style already exists
        existing_style = db.query(Style).filter(Style.id == style_data["id"]).first()
        if existing_style:
            print(f"  ⚠️  Style {style_data['name']} already exists, skipping...")
            continue
        
        style = Style(**style_data)
        db.add(style)
        print(f"  ✅ Added style: {style_data['name']}")
    
    db.commit()
    print(f"✅ Successfully populated {len(STYLES_DATA)} styles")

def main():
    """Main function to populate all data"""
    print("🚀 Starting database population...")
    
    # Initialize database
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Populate brands
        populate_brands(db)
        print()
        
        # Populate styles
        populate_styles(db)
        print()
        
        print("🎉 Database population completed successfully!")
        
    except Exception as e:
        print(f"❌ Error populating database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main() 