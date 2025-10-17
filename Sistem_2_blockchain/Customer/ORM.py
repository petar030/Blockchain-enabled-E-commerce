from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    categories = db.relationship(
        "Category",
        secondary="product_category",
        back_populates="products"
    )
    orders = db.relationship("OrderProduct", back_populates="product")


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    products = db.relationship(
        "Product",
        secondary="product_category",
        back_populates="categories"
    )


class ProductCategory(db.Model):
    __tablename__ = "product_category"

    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), primary_key=True)


class Order(db.Model):
    __tablename__ = "order"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(150), nullable=False)
    status = db.Column(
        db.Enum("CREATED", "PENDING", "COMPLETE", name="order_status"),
        nullable=False,
        default="CREATED"
    )
    timestamp = db.Column(db.DateTime, nullable=False)
    #dodatno polje za contract_id
    contract_address = db.Column(db.String(150), nullable=False)

    products = db.relationship("OrderProduct", back_populates="order")


class OrderProduct(db.Model):
    __tablename__ = "order_product"

    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="products")
    product = db.relationship("Product", back_populates="orders")
