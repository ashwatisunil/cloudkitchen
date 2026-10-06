from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin / Kitchen Manager'),
        ('STAFF', 'Staff'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STAFF')
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    CATEGORY_CHOICES = (
        ('Vegetables', 'Vegetables'),
        ('Dairy', 'Dairy'),
        ('Meat & Poultry', 'Meat & Poultry'),
        ('Grains & Bread', 'Grains & Bread'),
        ('Sauces & Spices', 'Sauces & Spices'),
        ('Beverages', 'Beverages'),
        ('Packaging', 'Packaging'),
        ('Other', 'Other'),
    )
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Vegetables')
    unit = models.CharField(max_length=20, help_text="e.g. kg, g, L, ml, pcs, slices")
    current_quantity = models.FloatField(default=0.0)
    min_stock_level = models.FloatField(default=10.0)
    max_stock_level = models.FloatField(default=100.0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='ingredients')
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_low_stock(self):
        return self.current_quantity <= self.min_stock_level

    @property
    def is_expiring_soon(self):
        if self.expiry_date:
            today = date.today()
            days = (self.expiry_date - today).days
            return 0 <= days <= 7
        return False

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < date.today()
        return False

    @property
    def total_value(self):
        return round(float(self.current_quantity) * float(self.unit_cost), 2)

    def __str__(self):
        return f"{self.name} ({self.current_quantity} {self.unit})"


class MenuItem(models.Model):
    CATEGORY_CHOICES = (
        ('Burgers', 'Burgers'),
        ('Pizzas', 'Pizzas'),
        ('Sides', 'Sides'),
        ('Beverages', 'Beverages'),
        ('Desserts', 'Desserts'),
        ('Combos', 'Combos'),
    )

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Burgers')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (₹{self.selling_price})"


class MenuItemIngredient(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='recipe_items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='used_in_items')
    quantity_required = models.FloatField(help_text="Amount of ingredient required per single menu item")

    class Meta:
        unique_together = ('menu_item', 'ingredient')

    def __str__(self):
        return f"{self.menu_item.name} requires {self.quantity_required} {self.ingredient.unit} of {self.ingredient.name}"


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('PURCHASE', 'Stock Purchase (In)'),
        ('USAGE', 'Ingredient Usage (Out)'),
        ('WASTAGE', 'Wastage Deduction'),
        ('ADJUSTMENT', 'Stock Adjustment'),
    )

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.FloatField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.total_cost and self.unit_cost and self.quantity:
            self.total_cost = round(float(self.unit_cost) * float(self.quantity), 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.ingredient.name} ({self.quantity} {self.ingredient.unit})"


class Wastage(models.Model):
    REASON_CHOICES = (
        ('Expired', 'Expired'),
        ('Spoiled', 'Spoiled'),
        ('Over-preparation', 'Over-preparation'),
        ('Damaged', 'Damaged'),
        ('Other', 'Other'),
    )

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='wastages')
    quantity = models.FloatField()
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, default='Spoiled')
    date = models.DateField(default=timezone.now)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.estimated_cost and self.ingredient:
            self.estimated_cost = round(float(self.ingredient.unit_cost) * float(self.quantity), 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Wastage: {self.quantity} {self.ingredient.unit} of {self.ingredient.name} ({self.reason})"


class SalesRecord(models.Model):
    WEATHER_CHOICES = (
        ('Sunny', 'Sunny'),
        ('Rainy', 'Rainy'),
        ('Cloudy', 'Cloudy'),
        ('Windy', 'Windy'),
    )

    EVENT_CHOICES = (
        ('None', 'None'),
        ('Festival', 'Festival'),
        ('Sports Match', 'Sports Match'),
        ('Weekend Promo', 'Weekend Promo'),
    )

    date = models.DateField()
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='sales_records')
    quantity_sold = models.IntegerField()
    day_of_week = models.IntegerField(help_text="0=Monday, 6=Sunday")
    month = models.IntegerField(help_text="1=Jan, 12=Dec")
    is_holiday = models.BooleanField(default=False)
    weather_condition = models.CharField(max_length=30, choices=WEATHER_CHOICES, default='Sunny')
    special_event = models.CharField(max_length=50, choices=EVENT_CHOICES, default='None')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - {self.menu_item.name}: {self.quantity_sold} sold"


class DemandPrediction(models.Model):
    prediction_date = models.DateField()
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='predictions')
    predicted_quantity = models.IntegerField()
    actual_quantity = models.IntegerField(null=True, blank=True)
    weather_condition = models.CharField(max_length=30, default='Sunny')
    is_holiday = models.BooleanField(default=False)
    special_event = models.CharField(max_length=50, default='None')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prediction for {self.menu_item.name} on {self.prediction_date}: {self.predicted_quantity}"
