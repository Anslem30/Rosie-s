from index import app, db, User, MenuItem
from werkzeug.security import generate_password_hash

def init_database():
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()

        print("Creating all tables...")
        db.create_all()

        # Create default users
        print("Creating default users...")
        default_user = User(
            username='user1',
            email='user1@example.com',
            password=generate_password_hash('password123'),
            full_name='John Doe',
            phone='+1234567890',
            address='123 Main Street'
        )

        admin_user = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            full_name='Admin User',
            phone='+9876543210',
            address='Admin Office'
        )

        db.session.add(default_user)
        db.session.add(admin_user)

        print("Adding Rosie’s real menu items...")

        menu_items = [

            # ---------------- APPETIZERS ----------------
            MenuItem(name='Puff Puff', price=5.99, category='Appetizers',
                     description='Sweet, fluffy fried dough balls.',
                     image='puff_puff.jpg'),

            MenuItem(name='Suya Chicken Wings', price=12.99, category='Appetizers',
                     description='Grilled chicken wings coated in suya spice.',
                     image='suya_chicken.jpg'),

            MenuItem(name='Peppered Chicken Wings', price=12.99, category='Appetizers',
                     description='Crispy wings tossed in spicy pepper sauce.',
                     image='chicken_wings.jpg'),

            MenuItem(name='Peppered Turkey Wings', price=12.99, category='Appetizers',
                     description='Tender turkey wings in bold pepper sauce.',
                     image='peppered_turkey.jpg'),

            # ---------------- MAIN COURSE ----------------
            MenuItem(name='Jollof Rice', price=14.99, category='Main Course',
                     description='Classic Nigerian jollof rice.',
                     image='jrice.jpg'),

            MenuItem(name='Jollof Spaghetti', price=10.99, category='Main Course',
                     description='Spaghetti cooked in jollof-style sauce.',
                     image='spag.jpg'),

            MenuItem(name='Fried Rice', price=16.99, category='Main Course',
                     description='Nigerian-style fried rice with vegetables.',
                     image='friedrice.jpg'),

            MenuItem(name='Ayamase', price=24.99, category='Main Course',
                     description='Spicy green ofada stew served with rice.',
                     image='ayamase.jpg'),

            # ---------------- SOUPS ----------------
            MenuItem(name='Egusi', price=20.99, category='Soups',
                     description='Ground melon seed soup with greens.',
                     image='egusi.jpg'),

            MenuItem(name='Efo-Riro', price=18.99, category='Soups',
                     description='Spinach stew cooked in rich pepper sauce.',
                     image='efoiro.jpg'),

            MenuItem(name='Okra', price=18.99, category='Soups',
                     description='Nigerian okra soup with assorted meats.',
                     image='okra.jpg'),

            # ---------------- SPECIAL MEALS ----------------
            MenuItem(name='Grilled Croaker Fish', price=15.99, category='Special Meals',
                     description='Whole croaker fish marinated and grilled.',
                     image='grilled fish.jpg'),

            MenuItem(name='Grilled Turkey', price=15.99, category='Special Meals',
                     description='Juicy grilled turkey seasoned with spices.',
                     image='turkey.jpg'),

            MenuItem(name='Chicken Suya Pizza', price=15.99, category='Special Meals',
                     description='Fusion of suya chicken and cheesy pizza.',
                     image='pizza.jpg'),

            # ---------------- SIDES ----------------
            MenuItem(name='Corn on the Cob', price=4.99, category='Sides',
                     description='Grilled corn on the cob.',
                     image='corn.jpg'),

            MenuItem(name='Fried Plantain', price=5.99, category='Sides',
                     description='Sweet fried plantain slices.',
                     image='plantain.jpg'),

            MenuItem(name='Coleslaw', price=3.99, category='Sides',
                     description='Creamy coleslaw salad.',
                     image='coleslaw.jpg'),

            MenuItem(name='Seasoned Fries', price=4.99, category='Sides',
                     description='Crispy seasoned fries.',
                     image='fries.jpg'),

            # ---------------- DRINKS ----------------
            MenuItem(name='Zobo', price=4.99, category='Drinks',
                     description='Hibiscus drink served chilled.',
                     image='zobo.jpg'),

            MenuItem(name='Soda', price=2.50, category='Drinks',
                     description='Assorted soft drinks.',
                     image='soda.jpg'),

            MenuItem(name='Water', price=1.50, category='Drinks',
                     description='Bottled water.',
                     image='water.jpg'),

            MenuItem(name='Malt', price=3.50, category='Drinks',
                     description='Classic malt drink.',
                     image='malt.jpg'),
        ]

        for item in menu_items:
            db.session.add(item)

        db.session.commit()

        print("\n✅ Rosie’s menu successfully loaded!")
        print(f"Total items added: {len(menu_items)}")
        print("Default login:")
        print("  user1 / password123")
        print("  admin / admin123")


if __name__ == '__main__':
    init_database()
