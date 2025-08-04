from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Brand, Style, Product, ProductStyle, Category, ProductVariant
import uuid

def populate_initial_data():
    init_db() # Ensure tables are created before populating data
    db: Session = SessionLocal()
    try:
        # Populate Brands
        brands_data = [
            {"name": "Nike", "slug": "nike", "logo": "https://example.com/logos/nike.png", "description": "Global leader in athletic footwear, apparel, equipment, accessories, and services."},
            {"name": "Adidas", "slug": "adidas", "logo": "https://example.com/logos/adidas.png", "description": "German multinational corporation, designs and manufactures shoes, clothing and accessories."},
            {"name": "Zara", "slug": "zara", "logo": "https://example.com/logos/zara.png", "description": "Spanish apparel retailer based in Arteixo, Galicia, Spain."},
            {"name": "H&M", "slug": "h&m", "logo": "https://example.com/logos/h&m.png", "description": "Swedish multinational clothing-retail company known for its fast-fashion clothing for men, women, teenagers and children."}
        ]
        for b_data in brands_data:
            if not db.query(Brand).filter(Brand.name == b_data["name"]).first():
                db.add(Brand(**b_data))
        db.commit()
        print("Brands populated.")

        # Populate Styles
        styles_data = [
            {"id": "casual", "name": "Casual", "description": "Relaxed, comfortable, and suitable for everyday wear.", "image": "https://example.com/styles/casual.jpg"},
            {"id": "sporty", "name": "Sporty", "description": "Athletic-inspired, comfortable, and functional.", "image": "https://example.com/styles/sporty.jpg"},
            {"id": "elegant", "name": "Elegant", "description": "Sophisticated, graceful, and refined.", "image": "https://example.com/styles/elegant.jpg"},
            {"id": "streetwear", "name": "Streetwear", "description": "Comfortable, casual clothing inspired by hip-hop and skate culture.", "image": "https://example.com/styles/streetwear.jpg"}
        ]
        for s_data in styles_data:
            if not db.query(Style).filter(Style.id == s_data["id"]).first():
                db.add(Style(**s_data))
        db.commit()
        print("Styles populated.")

        # Populate Categories
        categories_data = [
            {"id": "tshirts", "name": "T-Shirts", "description": "Casual tops for everyday wear."},
            {"id": "jeans", "name": "Jeans", "description": "Durable denim trousers."},
            {"id": "dresses", "name": "Dresses", "description": "One-piece garments for various occasions."},
            {"id": "sneakers", "name": "Sneakers", "description": "Athletic and casual footwear."},
            {"id": "hoodies", "name": "Hoodies", "description": "Comfortable hooded sweatshirts."}
        ]
        for c_data in categories_data:
            if not db.query(Category).filter(Category.id == c_data["id"]).first():
                db.add(Category(**c_data))
        db.commit()
        print("Categories populated.")

        # Retrieve populated brands, styles, and categories
        nike_brand = db.query(Brand).filter(Brand.name == "Nike").first()
        adidas_brand = db.query(Brand).filter(Brand.name == "Adidas").first()
        zara_brand = db.query(Brand).filter(Brand.name == "Zara").first()
        hm_brand = db.query(Brand).filter(Brand.name == "H&M").first()

        casual_style = db.query(Style).filter(Style.id == "casual").first()
        sporty_style = db.query(Style).filter(Style.id == "sporty").first()
        elegant_style = db.query(Style).filter(Style.id == "elegant").first()
        streetwear_style = db.query(Style).filter(Style.id == "streetwear").first()

        tshirts_category = db.query(Category).filter(Category.id == "tshirts").first()
        jeans_category = db.query(Category).filter(Category.id == "jeans").first()
        dresses_category = db.query(Category).filter(Category.id == "dresses").first()
        sneakers_category = db.query(Category).filter(Category.id == "sneakers").first()
        hoodies_category = db.query(Category).filter(Category.id == "hoodies").first()

        # Populate Products and ProductStyles
        products_data = [
            {
                "name": "Nike Air Max 270",
                "description": "Comfortable and stylish everyday sneakers.",
                "price": "150.00 р",
                "image_url": "https://example.com/products/nike_airmax.jpg",
                "sizes": ["S", "M", "L"],
                "brand": nike_brand,
                "category": sneakers_category,
                "styles": [sporty_style, casual_style]
            },
            {
                "name": "Adidas Ultraboost 22",
                "description": "Responsive running shoes for daily miles.",
                "price": "180.00 р",
                "image_url": "https://example.com/products/adidas_ultraboost.jpg",
                "sizes": ["XS", "S", "M"],
                "brand": adidas_brand,
                "category": sneakers_category,
                "styles": [sporty_style]
            },
            {
                "name": "Zara Flowy Midi Dress",
                "description": "Lightweight and elegant dress for any occasion.",
                "price": "79.99 р",
                "image_url": "https://example.com/products/zara_dress.jpg",
                "sizes": ["M", "L", "XL"],
                "brand": zara_brand,
                "category": dresses_category,
                "styles": [elegant_style, casual_style]
            },
            {
                "name": "H&M Oversized Hoodie",
                "description": "Cozy and trendy oversized hoodie.",
                "price": "35.00 р",
                "image_url": "https://example.com/products/hm_hoodie.jpg",
                "sizes": ["XS", "S"],
                "brand": hm_brand,
                "category": hoodies_category,
                "styles": [casual_style, streetwear_style]
            },
            {
                "name": "Nike Sportswear Tech Fleece",
                "description": "Premium fleece for warmth without the weight.",
                "price": "110.00 р",
                "image_url": "https://example.com/products/nike_techfleece.jpg",
                "sizes": ["S", "M", "L", "XL"],
                "brand": nike_brand,
                "category": hoodies_category,
                "styles": [sporty_style, casual_style, streetwear_style]
            }
        ]

        for p_data in products_data:
            if not db.query(Product).filter(Product.name == p_data["name"]).first():
                product = Product(
                    id=str(uuid.uuid4()),
                    name=p_data["name"],
                    description=p_data["description"],
                    price=p_data["price"],
                    image_url=p_data["image_url"],
                    brand_id=p_data["brand"].id,
                    category_id=p_data["category"].id
                )
                db.add(product)
                db.flush() # Flush to get product.id

                for size in p_data["sizes"]:
                    product_variant = ProductVariant(
                        product_id=product.id,
                        size=size,
                        stock_quantity=10 # Default stock quantity
                    )
                    db.add(product_variant)
                db.add(product)
                db.flush() # Flush to get product.id

                for style in p_data["styles"]:
                    product_style = ProductStyle(product_id=product.id, style_id=style.id)
                    db.add(product_style)
                print(f"Added product: {product.name}")
            else:
                print(f"Product already exists: {p_data['name']}")
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error populating data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Populating initial data (Brands, Styles, Products)...")
    populate_initial_data()
    print("Initial data population complete.")
