from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('accounts/login/', views.login_view),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Ingredients
    path('ingredients/', views.ingredient_list, name='ingredient_list'),
    path('ingredients/add/', views.ingredient_add, name='ingredient_add'),
    path('ingredients/edit/<int:pk>/', views.ingredient_edit, name='ingredient_edit'),
    path('ingredients/delete/<int:pk>/', views.ingredient_delete, name='ingredient_delete'),

    # Menu Items & Recipes
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/add/', views.menu_add, name='menu_add'),
    path('menu/edit/<int:pk>/', views.menu_edit, name='menu_edit'),
    path('menu/delete/<int:pk>/', views.menu_delete, name='menu_delete'),
    path('menu/<int:pk>/recipe/', views.recipe_manage, name='recipe_manage'),
    path('recipe/delete/<int:pk>/', views.recipe_delete, name='recipe_delete'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_add, name='supplier_add'),
    path('suppliers/edit/<int:pk>/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/delete/<int:pk>/', views.supplier_delete, name='supplier_delete'),

    # Inventory & Transactions
    path('inventory/', views.inventory_status, name='inventory_status'),
    path('inventory/add-stock/', views.add_stock, name='add_stock'),
    path('inventory/record-usage/', views.record_usage, name='record_usage'),
    path('inventory/transactions/', views.inventory_transactions, name='inventory_transactions'),

    # Wastage
    path('wastage/', views.wastage_list, name='wastage_list'),
    path('wastage/add/', views.wastage_add, name='wastage_add'),

    # Sales Data
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/add/', views.sales_add, name='sales_add'),

    # Demand Prediction & Reorder Recommendations
    path('prediction/', views.demand_prediction, name='demand_prediction'),
    path('reorders/', views.reorder_recommendations, name='reorder_recommendations'),

    # Reports & Analytics
    path('reports/', views.reports_view, name='reports'),
    path('analytics/', views.analytics_view, name='analytics'),

    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/toggle-role/<int:pk>/', views.user_toggle_role, name='user_toggle_role'),
]
