from django.contrib import admin
from .models import (
    UserProfile, Supplier, Ingredient, MenuItem, MenuItemIngredient,
    InventoryTransaction, Wastage, SalesRecord, DemandPrediction
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email')
    search_fields = ('name', 'contact_person')

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'current_quantity', 'unit', 'min_stock_level', 'unit_cost', 'supplier', 'expiry_date')
    list_filter = ('category', 'supplier')
    search_fields = ('name',)

class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'selling_price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name',)
    inlines = [MenuItemIngredientInline]

@admin.register(MenuItemIngredient)
class MenuItemIngredientAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'ingredient', 'quantity_required')

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'transaction_type', 'quantity', 'total_cost', 'performed_by', 'created_at')
    list_filter = ('transaction_type', 'created_at')

@admin.register(Wastage)
class WastageAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'quantity', 'reason', 'date', 'estimated_cost', 'reported_by')
    list_filter = ('reason', 'date')

@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'menu_item', 'quantity_sold', 'day_of_week', 'is_holiday', 'weather_condition', 'special_event')
    list_filter = ('menu_item', 'is_holiday', 'weather_condition', 'special_event')
    date_hierarchy = 'date'

@admin.register(DemandPrediction)
class DemandPredictionAdmin(admin.ModelAdmin):
    list_display = ('prediction_date', 'menu_item', 'predicted_quantity', 'actual_quantity', 'created_at')
    date_hierarchy = 'prediction_date'
