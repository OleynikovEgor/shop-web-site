# add_products.py
from data.reviews import Review
from data import db_session
from data.products import Product, ProductVariant

def main():
    db_session.global_init("db/Buyers.db")
    session = db_session.create_session()

    p1 = Product()
    session.add(p1)
    v1 = ProductVariant(
        product=p1,
        name="Casio 5600 series",
        type="Analog",
        price=50000,
        description="Классические элегантные часы",
        color_code="white",
        image_main="casio5600series1.jpg",
        image_1="casio5600series1.jpg"
    )
    v2 = ProductVariant(
        product=p1,
        name="Casio 5600 series",
        type="Analog",
        price=50000,
        description="Классические элегантные часы",
        color_code="black",
        image_main="casio5600series2.jpg",
        image_1="casio5600series2.jpg"
    )
    v3 = ProductVariant(
        product=p1,
        name="Casio 5600 series",
        type="Analog",
        price=50000,
        description="Классические элегантные часы",
        color_code="rainbow",
        image_main="casio5600series3.jpg",
        image_1="casio5600series3.jpg"
    )
    session.add(v1)
    session.add(v2)
    session.add(v3)
    session.commit()
    print("Добавлено 3 товара с вариантами.")

if __name__ == "__main__":
    main()
