from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from inventory_predictor.models import (
    Supplier, Ingredient, MenuItem, MenuItemIngredient,
    SalesRecord, Wastage, UserProfile
)
from inventory_predictor.ml_engine import DemandPredictionEngine

class InventoryModelTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name="Fresh Farm Produce",
            phone="1234567890",
            email="contact@freshfarm.com"
        )
        self.ingredient = Ingredient.objects.create(
            name="Tomato",
            category="Vegetables",
            unit="kg",
            current_quantity=5.0,
            min_stock_level=10.0,
            max_stock_level=50.0,
            unit_cost=40.00,
            supplier=self.supplier,
            expiry_date=date.today() + timedelta(days=3)
        )

    def test_ingredient_properties(self):
        self.assertTrue(self.ingredient.is_low_stock)
        self.assertTrue(self.ingredient.is_expiring_soon)
        self.assertFalse(self.ingredient.is_expired)
        self.assertEqual(self.ingredient.total_value, 200.0)

    def test_menu_item_and_recipe(self):
        burger = MenuItem.objects.create(
            name="Cheese Burger",
            category="Burgers",
            selling_price=150.00
        )
        recipe = MenuItemIngredient.objects.create(
            menu_item=burger,
            ingredient=self.ingredient,
            quantity_required=0.2
        )
        self.assertEqual(burger.recipe_items.count(), 1)
        self.assertEqual(recipe.quantity_required, 0.2)


class MLEngineTests(TestCase):
    def setUp(self):
        self.burger = MenuItem.objects.create(
            name="Veggie Burger",
            category="Burgers",
            selling_price=120.00
        )
        # Create 15 sales records for training test
        today = date.today()
        for i in range(15):
            SalesRecord.objects.create(
                date=today - timedelta(days=i),
                menu_item=self.burger,
                quantity_sold=30 + (i % 5),
                day_of_week=(today - timedelta(days=i)).weekday(),
                month=today.month,
                is_holiday=False,
                weather_condition='Sunny',
                special_event='None'
            )

    def test_ml_engine_training_and_prediction(self):
        engine = DemandPredictionEngine()
        success, msg = engine.train_model()
        self.assertTrue(success)
        self.assertTrue(engine.is_trained)

        predictions = engine.predict_for_date(date.today() + timedelta(days=1))
        self.assertEqual(len(predictions), 1)
        self.assertGreater(predictions[0]['predicted_demand'], 0)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            password="password123",
            email="admin@test.com"
        )
        UserProfile.objects.create(user=self.admin_user, role='ADMIN')

    def test_dashboard_access_authenticated(self):
        self.client.login(username="admin_test", password="password123")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_ingredient_list_authenticated(self):
        self.client.login(username="admin_test", password="password123")
        response = self.client.get(reverse('ingredient_list'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_renders(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_inventory_status_filtered(self):
        self.client.login(username="admin_test", password="password123")
        response = self.client.get(reverse('inventory_status') + '?status=low_stock')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['status_filter'], 'low_stock')

    def test_supplier_list_view(self):
        self.client.login(username="admin_test", password="password123")
        response = self.client.get(reverse('supplier_list'))
        self.assertEqual(response.status_code, 200)

    def test_ingredient_list_supplier_filtered(self):
        self.client.login(username="admin_test", password="password123")
        sup = Supplier.objects.create(name="Test Vendor")
        response = self.client.get(reverse('ingredient_list') + f'?supplier={sup.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['supplier_filter'], str(sup.id))
