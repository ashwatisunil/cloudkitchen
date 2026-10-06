import random
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory_predictor.models import (
    UserProfile, Supplier, Ingredient, MenuItem, MenuItemIngredient,
    InventoryTransaction, Wastage, SalesRecord
)
from inventory_predictor.ml_engine import ml_engine

class Command(BaseCommand):
    help = 'Seeds database with realistic initial cloud kitchen data and 60-day historical sales.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting Cloud Kitchen Data Seeding...'))

        # 1. Create Users & Profiles
        admin_user, created = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@cloudkitchen.com',
            'first_name': 'Kitchen',
            'last_name': 'Manager',
            'is_staff': True,
            'is_superuser': True
        })
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.create(user=admin_user, role='ADMIN', phone='+91 9876543210')
            self.stdout.write(self.style.SUCCESS('Created Admin user: admin / admin123'))
        else:
            UserProfile.objects.get_or_create(user=admin_user, defaults={'role': 'ADMIN'})

        staff_user, created = User.objects.get_or_create(username='staff', defaults={
            'email': 'staff@cloudkitchen.com',
            'first_name': 'Kitchen',
            'last_name': 'Staff',
            'is_staff': False,
            'is_superuser': False
        })
        if created:
            staff_user.set_password('staff123')
            staff_user.save()
            UserProfile.objects.create(user=staff_user, role='STAFF', phone='+91 9876543211')
            self.stdout.write(self.style.SUCCESS('Created Staff user: staff / staff123'))
        else:
            UserProfile.objects.get_or_create(user=staff_user, defaults={'role': 'STAFF'})

        # 2. Create Suppliers
        suppliers_data = [
            {'name': 'Fresh Farms Organic', 'contact_person': 'Ramesh Kumar', 'phone': '9876500001', 'email': 'ramesh@freshfarms.com', 'address': 'Sector 12, Market Yard'},
            {'name': 'Quality Dairy & Cheese Co.', 'contact_person': 'Suresh Patel', 'phone': '9876500002', 'email': 'suresh@qualitydairy.com', 'address': 'Industrial Area Phase 1'},
            {'name': 'Prime Meats & Poultry', 'contact_person': 'Anil Sharma', 'phone': '9876500003', 'email': 'orders@primemeats.com', 'address': 'Cold Storage Hub 4'},
            {'name': 'Global Bakers & Grain Supplies', 'contact_person': 'Priya Singh', 'phone': '9876500004', 'email': 'priya@globalbakers.com', 'address': 'Baker Street Hub'},
            {'name': 'Beverage World & Packaging', 'contact_person': 'Amit Verma', 'phone': '9876500005', 'email': 'amit@bevworld.com', 'address': 'Logistics Park, Gateway'},
        ]

        suppliers_map = {}
        for s in suppliers_data:
            obj, _ = Supplier.objects.get_or_create(name=s['name'], defaults=s)
            suppliers_map[s['name']] = obj

        # 3. Create Ingredients
        today = date.today()
        ingredients_data = [
            {'name': 'Chicken Breast', 'category': 'Meat & Poultry', 'unit': 'kg', 'current_quantity': 18.5, 'min_stock_level': 10.0, 'max_stock_level': 50.0, 'unit_cost': 240.0, 'supplier': suppliers_map['Prime Meats & Poultry'], 'expiry_date': today + timedelta(days=5)},
            {'name': 'Burger Buns', 'category': 'Grains & Bread', 'unit': 'pcs', 'current_quantity': 110.0, 'min_stock_level': 50.0, 'max_stock_level': 200.0, 'unit_cost': 6.0, 'supplier': suppliers_map['Global Bakers & Grain Supplies'], 'expiry_date': today + timedelta(days=4)},
            {'name': 'Cheddar Cheese Slices', 'category': 'Dairy', 'unit': 'slices', 'current_quantity': 75.0, 'min_stock_level': 40.0, 'max_stock_level': 150.0, 'unit_cost': 8.5, 'supplier': suppliers_map['Quality Dairy & Cheese Co.'], 'expiry_date': today + timedelta(days=15)},
            {'name': 'Fresh Tomatoes', 'category': 'Vegetables', 'unit': 'kg', 'current_quantity': 8.0, 'min_stock_level': 12.0, 'max_stock_level': 40.0, 'unit_cost': 35.0, 'supplier': suppliers_map['Fresh Farms Organic'], 'expiry_date': today + timedelta(days=3)}, # Low Stock!
            {'name': 'Crisp Lettuce', 'category': 'Vegetables', 'unit': 'kg', 'current_quantity': 3.5, 'min_stock_level': 5.0, 'max_stock_level': 20.0, 'unit_cost': 55.0, 'supplier': suppliers_map['Fresh Farms Organic'], 'expiry_date': today + timedelta(days=2)}, # Low Stock & Expiring!
            {'name': 'Pizza Crust 10-inch', 'category': 'Grains & Bread', 'unit': 'pcs', 'current_quantity': 30.0, 'min_stock_level': 25.0, 'max_stock_level': 100.0, 'unit_cost': 28.0, 'supplier': suppliers_map['Global Bakers & Grain Supplies'], 'expiry_date': today + timedelta(days=6)},
            {'name': 'Mozzarella Cheese', 'category': 'Dairy', 'unit': 'kg', 'current_quantity': 6.5, 'min_stock_level': 8.0, 'max_stock_level': 30.0, 'unit_cost': 380.0, 'supplier': suppliers_map['Quality Dairy & Cheese Co.'], 'expiry_date': today + timedelta(days=12)}, # Low Stock!
            {'name': 'Pepperoni Slices', 'category': 'Meat & Poultry', 'unit': 'kg', 'current_quantity': 4.0, 'min_stock_level': 3.0, 'max_stock_level': 15.0, 'unit_cost': 520.0, 'supplier': suppliers_map['Prime Meats & Poultry'], 'expiry_date': today + timedelta(days=25)},
            {'name': 'Potato Fries Stock', 'category': 'Vegetables', 'unit': 'kg', 'current_quantity': 22.0, 'min_stock_level': 15.0, 'max_stock_level': 60.0, 'unit_cost': 85.0, 'supplier': suppliers_map['Fresh Farms Organic'], 'expiry_date': today + timedelta(days=45)},
            {'name': 'Refined Cooking Oil', 'category': 'Sauces & Spices', 'unit': 'L', 'current_quantity': 16.0, 'min_stock_level': 10.0, 'max_stock_level': 40.0, 'unit_cost': 145.0, 'supplier': suppliers_map['Global Bakers & Grain Supplies'], 'expiry_date': today + timedelta(days=90)},
            {'name': 'Cola Cans 330ml', 'category': 'Beverages', 'unit': 'pcs', 'current_quantity': 140.0, 'min_stock_level': 40.0, 'max_stock_level': 300.0, 'unit_cost': 25.0, 'supplier': suppliers_map['Beverage World & Packaging'], 'expiry_date': today + timedelta(days=120)},
        ]

        ing_map = {}
        for ing in ingredients_data:
            obj, _ = Ingredient.objects.get_or_create(name=ing['name'], defaults=ing)
            ing_map[ing['name']] = obj

        # 4. Create Menu Items
        menu_items_data = [
            {'name': 'Classic Chicken Burger', 'category': 'Burgers', 'selling_price': 180.0, 'is_available': True, 'description': 'Juicy grilled chicken patty with fresh lettuce, tomatoes and cheese.'},
            {'name': 'Veg Supreme Burger', 'category': 'Burgers', 'selling_price': 140.0, 'is_available': True, 'description': 'Crispy veg patty served with cheese slice and crunchy lettuce.'},
            {'name': 'Classic Margherita Pizza', 'category': 'Pizzas', 'selling_price': 290.0, 'is_available': True, 'description': '10-inch hand-tossed pizza with rich tomato sauce and melted mozzarella.'},
            {'name': 'Pepperoni Feast Pizza', 'category': 'Pizzas', 'selling_price': 390.0, 'is_available': True, 'description': 'Loaded with premium sliced pepperoni and double mozzarella.'},
            {'name': 'Crispy Potato French Fries', 'category': 'Sides', 'selling_price': 95.0, 'is_available': True, 'description': 'Golden deep-fried salted potato fries.'},
            {'name': 'Chilled Cola Can', 'category': 'Beverages', 'selling_price': 50.0, 'is_available': True, 'description': '330ml chilled carbonated cola beverage.'},
        ]

        menu_map = {}
        for m in menu_items_data:
            obj, _ = MenuItem.objects.get_or_create(name=m['name'], defaults=m)
            menu_map[m['name']] = obj

        # 5. Create MenuItemIngredients (Recipes)
        recipes = [
            ('Classic Chicken Burger', [('Chicken Breast', 0.150), ('Burger Buns', 1.0), ('Cheddar Cheese Slices', 1.0), ('Fresh Tomatoes', 0.030), ('Crisp Lettuce', 0.020)]),
            ('Veg Supreme Burger', [('Burger Buns', 1.0), ('Cheddar Cheese Slices', 1.0), ('Fresh Tomatoes', 0.040), ('Crisp Lettuce', 0.030)]),
            ('Classic Margherita Pizza', [('Pizza Crust 10-inch', 1.0), ('Mozzarella Cheese', 0.150), ('Fresh Tomatoes', 0.100)]),
            ('Pepperoni Feast Pizza', [('Pizza Crust 10-inch', 1.0), ('Mozzarella Cheese', 0.180), ('Pepperoni Slices', 0.080)]),
            ('Crispy Potato French Fries', [('Potato Fries Stock', 0.200), ('Refined Cooking Oil', 0.050)]),
            ('Chilled Cola Can', [('Cola Cans 330ml', 1.0)]),
        ]

        for dish_name, ingredients_list in recipes:
            dish = menu_map[dish_name]
            for ing_name, qty in ingredients_list:
                ing_obj = ing_map[ing_name]
                MenuItemIngredient.objects.get_or_create(
                    menu_item=dish,
                    ingredient=ing_obj,
                    defaults={'quantity_required': qty}
                )

        # 6. Create Historical Sales Data (Last 60 Days)
        self.stdout.write('Generating 60 days of historical sales records...')
        start_date = today - timedelta(days=60)

        SalesRecord.objects.all().delete()

        sales_records = []
        weathers = ['Sunny', 'Sunny', 'Sunny', 'Rainy', 'Cloudy', 'Windy']
        events = ['None', 'None', 'None', 'None', 'Festival', 'Sports Match', 'Weekend Promo']

        for i in range(60):
            current_date = start_date + timedelta(days=i)
            day_of_week = current_date.weekday()
            month = current_date.month
            is_weekend = day_of_week >= 5
            is_holiday = is_weekend or (i % 15 == 0)

            weather = random.choice(weathers)
            event = 'Weekend Promo' if is_weekend and random.random() > 0.5 else random.choice(events)

            for dish_name, dish_obj in menu_map.items():
                if dish_name == 'Classic Chicken Burger':
                    base_sales = 45
                elif dish_name == 'Veg Supreme Burger':
                    base_sales = 35
                elif dish_name == 'Classic Margherita Pizza':
                    base_sales = 30
                elif dish_name == 'Pepperoni Feast Pizza':
                    base_sales = 25
                elif dish_name == 'Crispy Potato French Fries':
                    base_sales = 55
                else:
                    base_sales = 60

                multiplier = 1.0
                if day_of_week == 4:
                    multiplier *= 1.25
                elif day_of_week == 5:
                    multiplier *= 1.55
                elif day_of_week == 6:
                    multiplier *= 1.45

                if is_holiday:
                    multiplier *= 1.20
                if weather == 'Rainy':
                    multiplier *= 1.15
                if event == 'Sports Match':
                    multiplier *= 1.35
                elif event == 'Festival':
                    multiplier *= 1.30

                noise = random.uniform(0.9, 1.1)
                final_qty = int(round(base_sales * multiplier * noise))

                sales_records.append(SalesRecord(
                    date=current_date,
                    menu_item=dish_obj,
                    quantity_sold=final_qty,
                    day_of_week=day_of_week,
                    month=month,
                    is_holiday=is_holiday,
                    weather_condition=weather,
                    special_event=event
                ))

        SalesRecord.objects.bulk_create(sales_records)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(sales_records)} historical sales records!'))

        # 7. Create Sample Inventory Transactions & Wastage
        InventoryTransaction.objects.all().delete()
        Wastage.objects.all().delete()

        for ing in Ingredient.objects.all():
            unit_cost_val = float(ing.unit_cost)
            # Initial purchase transaction
            InventoryTransaction.objects.create(
                ingredient=ing,
                transaction_type='PURCHASE',
                quantity=ing.current_quantity * 1.5,
                unit_cost=ing.unit_cost,
                total_cost=unit_cost_val * (ing.current_quantity * 1.5),
                performed_by=admin_user,
                notes='Initial stock inward purchase from supplier'
            )
            # Usage transaction
            InventoryTransaction.objects.create(
                ingredient=ing,
                transaction_type='USAGE',
                quantity=ing.current_quantity * 0.4,
                unit_cost=ing.unit_cost,
                total_cost=unit_cost_val * (ing.current_quantity * 0.4),
                performed_by=staff_user,
                notes='Kitchen daily meal prep usage'
            )

        # Sample Wastage Records
        lettuce = ing_map['Crisp Lettuce']
        tomatoes = ing_map['Fresh Tomatoes']
        Wastage.objects.create(
            ingredient=lettuce,
            quantity=1.2,
            reason='Expired',
            date=today - timedelta(days=2),
            estimated_cost=1.2 * float(lettuce.unit_cost),
            reported_by=staff_user,
            notes='Lettuce leaves wilted due to fridge temperature fluctuation'
        )
        Wastage.objects.create(
            ingredient=tomatoes,
            quantity=0.8,
            reason='Spoiled',
            date=today - timedelta(days=1),
            estimated_cost=0.8 * float(tomatoes.unit_cost),
            reported_by=staff_user,
            notes='Over-ripe tomatoes softened'
        )

        # 8. Train ML Model
        self.stdout.write('Training initial Random Forest ML model on historical sales data...')
        success, msg = ml_engine.train_model()
        if success:
            self.stdout.write(self.style.SUCCESS(f'ML Model Trained Successfully! R2: {ml_engine.metrics["r2_score"]}, MAE: {ml_engine.metrics["mae"]}'))
        else:
            self.stdout.write(self.style.WARNING(f'ML Model training warning: {msg}'))

        self.stdout.write(self.style.SUCCESS('\n==========================================='))
        self.stdout.write(self.style.SUCCESS('Cloud Kitchen Database Seeding Completed!'))
        self.stdout.write(self.style.SUCCESS('Default Credentials:'))
        self.stdout.write(self.style.SUCCESS('  Admin Login: username="admin", password="admin123"'))
        self.stdout.write(self.style.SUCCESS('  Staff Login: username="staff", password="staff123"'))
        self.stdout.write(self.style.SUCCESS('===========================================\n'))
