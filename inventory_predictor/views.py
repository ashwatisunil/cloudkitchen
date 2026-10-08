import json
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, F, Q, Avg
from django.http import JsonResponse
from django.core.management import call_command

from .models import (
    UserProfile, Supplier, Ingredient, MenuItem, MenuItemIngredient,
    InventoryTransaction, Wastage, SalesRecord, DemandPrediction
)
from .forms import (
    SupplierForm, IngredientForm, MenuItemForm, MenuItemIngredientForm,
    AddStockForm, RecordUsageForm, WastageForm, SalesRecordForm, UserManagementForm
)
from .ml_engine import ml_engine

def role_check_admin(user):
    if not user.is_authenticated:
        return False
    try:
        return user.is_superuser or user.profile.role == 'ADMIN'
    except Exception:
        return user.is_superuser

# ==========================================
# 1. AUTHENTICATION MODULE
# ==========================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Ensure UserProfile exists
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'ADMIN' if user.is_superuser else 'STAFF'})
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'inventory_predictor/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


# ==========================================
# 2. DASHBOARD MODULE
# ==========================================
@login_required
def dashboard(request):
    # Ensure sample data exists if database is totally empty
    if Ingredient.objects.count() == 0 and SalesRecord.objects.count() == 0:
        try:
            call_command('seed_data')
        except Exception:
            pass

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Top KPI Cards Data
    total_ingredients = Ingredient.objects.count()
    low_stock_list = [i for i in Ingredient.objects.all() if i.is_low_stock]
    expiring_soon_list = [i for i in Ingredient.objects.all() if i.is_expiring_soon]
    total_menu_items = MenuItem.objects.count()

    # Today's Sales
    today_sales_records = SalesRecord.objects.filter(date=today)
    today_sales_qty = today_sales_records.aggregate(Sum('quantity_sold'))['quantity_sold__sum'] or 0
    today_sales_rev = sum(s.quantity_sold * float(s.menu_item.selling_price) for s in today_sales_records.select_related('menu_item'))

    # Tomorrow's Predicted Demand
    predictions = ml_engine.predict_for_date(tomorrow)
    total_predicted_demand = sum(p['predicted_demand'] for p in predictions)

    # Recent Data
    recent_transactions = InventoryTransaction.objects.select_related('ingredient', 'performed_by').order_by('-created_at')[:8]
    recent_wastage = Wastage.objects.select_related('ingredient', 'reported_by').order_by('-date')[:5]

    # Dashboard Sales Trend (Last 14 days)
    fourteen_days_ago = today - timedelta(days=14)
    sales_by_date = SalesRecord.objects.filter(date__gte=fourteen_days_ago)\
        .values('date')\
        .annotate(total_qty=Sum('quantity_sold'))\
        .order_by('date')

    chart_dates = [s['date'].strftime('%b %d') for s in sales_by_date]
    chart_sales = [s['total_qty'] for s in sales_by_date]

    # Top Selling Menu Items
    top_items_data = SalesRecord.objects.values('menu_item__name')\
        .annotate(total_sold=Sum('quantity_sold'))\
        .order_by('-total_sold')[:5]

    top_item_labels = [item['menu_item__name'] for item in top_items_data]
    top_item_counts = [item['total_sold'] for item in top_items_data]

    context = {
        'total_ingredients': total_ingredients,
        'low_stock_count': len(low_stock_list),
        'expiring_soon_count': len(expiring_soon_list),
        'total_menu_items': total_menu_items,
        'today_sales_qty': today_sales_qty,
        'today_sales_rev': round(today_sales_rev, 2),
        'total_predicted_demand': total_predicted_demand,
        'low_stock_list': low_stock_list[:6],
        'expiring_soon_list': expiring_soon_list[:6],
        'recent_transactions': recent_transactions,
        'recent_wastage': recent_wastage,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_sales_json': json.dumps(chart_sales),
        'top_item_labels_json': json.dumps(top_item_labels),
        'top_item_counts_json': json.dumps(top_item_counts),
        'predictions': predictions[:6],
    }

    return render(request, 'inventory_predictor/dashboard.html', context)


# ==========================================
# 3. INGREDIENT MANAGEMENT MODULE
# ==========================================
@login_required
def ingredient_list(request):
    ingredients = Ingredient.objects.select_related('supplier').all()

    # Search & Filter
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()
    supplier_filter = request.GET.get('supplier', '').strip()

    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)

    if category_filter:
        ingredients = ingredients.filter(category=category_filter)

    if supplier_filter:
        ingredients = ingredients.filter(supplier_id=supplier_filter)

    ingredients_list = list(ingredients)
    if status_filter == 'low_stock':
        ingredients_list = [i for i in ingredients_list if i.is_low_stock]
    elif status_filter == 'expiring':
        ingredients_list = [i for i in ingredients_list if i.is_expiring_soon]

    categories = Ingredient.CATEGORY_CHOICES
    suppliers = Supplier.objects.all()

    context = {
        'ingredients': ingredients_list,
        'categories': categories,
        'suppliers': suppliers,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'supplier_filter': supplier_filter,
        'is_admin': role_check_admin(request.user)
    }
    return render(request, 'inventory_predictor/ingredients/list.html', context)


@login_required
def ingredient_add(request):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin / Kitchen Managers can add ingredients.")
        return redirect('ingredient_list')

    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            ingredient = form.save()
            messages.success(request, f"Ingredient '{ingredient.name}' added successfully!")
            return redirect('ingredient_list')
    else:
        form = IngredientForm()

    return render(request, 'inventory_predictor/ingredients/form.html', {'form': form, 'title': 'Add New Ingredient'})


@login_required
def ingredient_edit(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin / Kitchen Managers can edit ingredients.")
        return redirect('ingredient_list')

    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ingredient '{ingredient.name}' updated successfully!")
            return redirect('ingredient_list')
    else:
        form = IngredientForm(instance=ingredient)

    return render(request, 'inventory_predictor/ingredients/form.html', {'form': form, 'title': f'Edit Ingredient - {ingredient.name}'})


@login_required
def ingredient_delete(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin / Kitchen Managers can delete ingredients.")
        return redirect('ingredient_list')

    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        name = ingredient.name
        ingredient.delete()
        messages.success(request, f"Ingredient '{name}' deleted successfully!")
        return redirect('ingredient_list')

    return render(request, 'inventory_predictor/confirm_delete.html', {
        'object': ingredient,
        'type': 'Ingredient',
        'cancel_url': 'ingredient_list'
    })


# ==========================================
# 4. MENU ITEM MANAGEMENT MODULE
# ==========================================
@login_required
def menu_list(request):
    menu_items = MenuItem.objects.prefetch_related('recipe_items__ingredient').all()
    categories = MenuItem.CATEGORY_CHOICES

    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()

    if search_query:
        menu_items = menu_items.filter(name__icontains=search_query)

    if category_filter:
        menu_items = menu_items.filter(category=category_filter)

    context = {
        'menu_items': menu_items,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'is_admin': role_check_admin(request.user)
    }
    return render(request, 'inventory_predictor/menu/list.html', context)


@login_required
def menu_add(request):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin / Kitchen Managers can add menu items.")
        return redirect('menu_list')

    if request.method == 'POST':
        form = MenuItemForm(request.POST)
        if form.is_valid():
            menu_item = form.save()
            messages.success(request, f"Menu item '{menu_item.name}' created! Now add required ingredients.")
            return redirect('recipe_manage', pk=menu_item.pk)
    else:
        form = MenuItemForm()

    return render(request, 'inventory_predictor/menu/form.html', {'form': form, 'title': 'Add New Menu Item'})


@login_required
def menu_edit(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin / Kitchen Managers can edit menu items.")
        return redirect('menu_list')

    menu_item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        form = MenuItemForm(request.POST, instance=menu_item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Menu item '{menu_item.name}' updated successfully!")
            return redirect('menu_list')
    else:
        form = MenuItemForm(instance=menu_item)

    return render(request, 'inventory_predictor/menu/form.html', {'form': form, 'title': f'Edit Menu Item - {menu_item.name}'})


@login_required
def menu_delete(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin / Kitchen Managers can delete menu items.")
        return redirect('menu_list')

    menu_item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        name = menu_item.name
        menu_item.delete()
        messages.success(request, f"Menu item '{name}' deleted successfully!")
        return redirect('menu_list')

    return render(request, 'inventory_predictor/confirm_delete.html', {
        'object': menu_item,
        'type': 'Menu Item',
        'cancel_url': 'menu_list'
    })


@login_required
def recipe_manage(request, pk):
    menu_item = get_object_or_404(MenuItem, pk=pk)
    recipe_items = MenuItemIngredient.objects.filter(menu_item=menu_item).select_related('ingredient')

    if request.method == 'POST':
        if not role_check_admin(request.user):
            messages.error(request, "Access Denied. Only Admin / Kitchen Managers can edit recipes.")
            return redirect('menu_list')

        form = MenuItemIngredientForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.menu_item = menu_item
            try:
                recipe.save()
                messages.success(request, f"Added {recipe.ingredient.name} to {menu_item.name} recipe!")
            except Exception:
                messages.error(request, f"Ingredient {recipe.ingredient.name} is already in recipe.")
            return redirect('recipe_manage', pk=menu_item.pk)
    else:
        form = MenuItemIngredientForm()

    context = {
        'menu_item': menu_item,
        'recipe_items': recipe_items,
        'form': form,
        'is_admin': role_check_admin(request.user)
    }
    return render(request, 'inventory_predictor/menu/recipe.html', context)


@login_required
def recipe_delete(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied.")
        return redirect('menu_list')

    recipe_item = get_object_or_404(MenuItemIngredient, pk=pk)
    menu_item_id = recipe_item.menu_item.id
    recipe_item.delete()
    messages.success(request, "Ingredient removed from recipe.")
    return redirect('recipe_manage', pk=menu_item_id)


# ==========================================
# 5. SUPPLIER MANAGEMENT MODULE
# ==========================================
@login_required
def supplier_list(request):
    suppliers = Supplier.objects.prefetch_related('ingredients').annotate(total_ingredients=Count('ingredients')).all()
    return render(request, 'inventory_predictor/suppliers/list.html', {
        'suppliers': suppliers,
        'is_admin': role_check_admin(request.user)
    })


@login_required
def supplier_add(request):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin can add suppliers.")
        return redirect('supplier_list')

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.name}' added successfully!")
            return redirect('supplier_list')
    else:
        form = SupplierForm()

    return render(request, 'inventory_predictor/suppliers/form.html', {'form': form, 'title': 'Add Supplier'})


@login_required
def supplier_edit(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied.")
        return redirect('supplier_list')

    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' updated successfully!")
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'inventory_predictor/suppliers/form.html', {'form': form, 'title': f'Edit Supplier - {supplier.name}'})


@login_required
def supplier_delete(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied.")
        return redirect('supplier_list')

    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier '{name}' deleted!")
        return redirect('supplier_list')

    return render(request, 'inventory_predictor/confirm_delete.html', {
        'object': supplier,
        'type': 'Supplier',
        'cancel_url': 'supplier_list'
    })


# ==========================================
# 6. INVENTORY TRANSACTIONS & STOCK MODULE
# ==========================================
@login_required
def inventory_status(request):
    ingredients = Ingredient.objects.select_related('supplier').all()
    status_filter = request.GET.get('status', '').strip()

    total_stock_value = sum(i.total_value for i in ingredients)
    low_stock_count = sum(1 for i in ingredients if i.is_low_stock)

    ingredients_list = list(ingredients)
    if status_filter == 'low_stock':
        ingredients_list = [i for i in ingredients_list if i.is_low_stock]
    elif status_filter == 'normal':
        ingredients_list = [i for i in ingredients_list if not i.is_low_stock]

    context = {
        'ingredients': ingredients_list,
        'total_stock_value': round(total_stock_value, 2),
        'low_stock_count': low_stock_count,
        'status_filter': status_filter,
        'is_admin': role_check_admin(request.user)
    }
    return render(request, 'inventory_predictor/inventory/status.html', context)


@login_required
def add_stock(request):
    if request.method == 'POST':
        form = AddStockForm(request.POST)
        if form.is_valid():
            ing = form.cleaned_data['ingredient']
            qty = form.cleaned_data['quantity']
            unit_cost = form.cleaned_data['unit_cost'] or ing.unit_cost
            notes = form.cleaned_data['notes']

            # Update ingredient stock
            ing.current_quantity += qty
            ing.unit_cost = unit_cost
            ing.save()

            # Record Inventory Transaction
            InventoryTransaction.objects.create(
                ingredient=ing,
                transaction_type='PURCHASE',
                quantity=qty,
                unit_cost=unit_cost,
                total_cost=float(unit_cost) * float(qty),
                performed_by=request.user,
                notes=notes or 'Inward stock purchase'
            )

            messages.success(request, f"Successfully added {qty} {ing.unit} to {ing.name} stock!")
            return redirect('inventory_status')
    else:
        form = AddStockForm()

    return render(request, 'inventory_predictor/inventory/add_stock.html', {'form': form})


@login_required
def record_usage(request):
    if request.method == 'POST':
        form = RecordUsageForm(request.POST)
        if form.is_valid():
            ing = form.cleaned_data['ingredient']
            qty = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']

            if qty > ing.current_quantity:
                messages.error(request, f"Cannot deduct {qty} {ing.unit}. Only {ing.current_quantity} {ing.unit} currently in stock.")
            else:
                ing.current_quantity -= qty
                ing.save()

                InventoryTransaction.objects.create(
                    ingredient=ing,
                    transaction_type='USAGE',
                    quantity=qty,
                    unit_cost=ing.unit_cost,
                    total_cost=float(ing.unit_cost) * float(qty),
                    performed_by=request.user,
                    notes=notes or 'Kitchen usage'
                )

                messages.success(request, f"Recorded usage of {qty} {ing.unit} for {ing.name}.")
                return redirect('inventory_status')
    else:
        form = RecordUsageForm()

    return render(request, 'inventory_predictor/inventory/record_usage.html', {'form': form})


@login_required
def inventory_transactions(request):
    transactions = InventoryTransaction.objects.select_related('ingredient', 'performed_by').order_by('-created_at')
    
    tx_type = request.GET.get('type', '')
    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)

    return render(request, 'inventory_predictor/inventory/transactions.html', {
        'transactions': transactions,
        'selected_type': tx_type
    })


# ==========================================
# 7. WASTAGE MANAGEMENT MODULE
# ==========================================
@login_required
def wastage_list(request):
    wastages = Wastage.objects.select_related('ingredient', 'reported_by').order_by('-date')
    total_cost = wastages.aggregate(Sum('estimated_cost'))['estimated_cost__sum'] or 0.0

    return render(request, 'inventory_predictor/wastage/list.html', {
        'wastages': wastages,
        'total_cost': round(float(total_cost), 2),
        'is_admin': role_check_admin(request.user)
    })


@login_required
def wastage_add(request):
    if request.method == 'POST':
        form = WastageForm(request.POST)
        if form.is_valid():
            wastage = form.save(commit=False)
            ing = wastage.ingredient

            if wastage.quantity > ing.current_quantity:
                messages.warning(request, f"Wasted quantity ({wastage.quantity}) exceeds current stock ({ing.current_quantity}). Stock reduced to 0.")
                ing.current_quantity = 0.0
            else:
                ing.current_quantity -= wastage.quantity

            ing.save()

            wastage.estimated_cost = round(float(ing.unit_cost) * float(wastage.quantity), 2)
            wastage.reported_by = request.user
            wastage.save()

            # Record in Inventory Transaction
            InventoryTransaction.objects.create(
                ingredient=ing,
                transaction_type='WASTAGE',
                quantity=wastage.quantity,
                unit_cost=ing.unit_cost,
                total_cost=wastage.estimated_cost,
                performed_by=request.user,
                notes=f"Wastage recorded: {wastage.reason}"
            )

            messages.success(request, f"Wastage record saved! Deducted {wastage.quantity} {ing.unit} from {ing.name} stock.")
            return redirect('wastage_list')
    else:
        form = WastageForm(initial={'date': date.today()})

    return render(request, 'inventory_predictor/wastage/form.html', {'form': form})


# ==========================================
# 8. SALES / DEMAND DATA MODULE
# ==========================================
@login_required
def sales_list(request):
    sales_records = SalesRecord.objects.select_related('menu_item').order_by('-date', 'menu_item__name')
    
    item_filter = request.GET.get('menu_item', '')
    if item_filter:
        sales_records = sales_records.filter(menu_item_id=item_filter)

    menu_items = MenuItem.objects.all()

    return render(request, 'inventory_predictor/sales/list.html', {
        'sales_records': sales_records[:100],
        'menu_items': menu_items,
        'selected_item': item_filter
    })


@login_required
def sales_add(request):
    if request.method == 'POST':
        form = SalesRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.day_of_week = record.date.weekday()
            record.month = record.date.month
            record.save()

            messages.success(request, f"Sales record added for {record.menu_item.name} on {record.date}!")
            return redirect('sales_list')
    else:
        form = SalesRecordForm(initial={'date': date.today()})

    return render(request, 'inventory_predictor/sales/form.html', {'form': form})


# ==========================================
# 9. DEMAND PREDICTION MODULE
# ==========================================
@login_required
def demand_prediction(request):
    target_date_str = request.GET.get('date', (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"))
    weather = request.GET.get('weather', 'Sunny')
    is_holiday = request.GET.get('is_holiday', '0') == '1'
    special_event = request.GET.get('special_event', 'None')

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except Exception:
        target_date = date.today() + timedelta(days=1)
        target_date_str = target_date.strftime("%Y-%m-%d")

    # Retrain trigger
    if request.GET.get('action') == 'retrain':
        if role_check_admin(request.user):
            success, msg = ml_engine.train_model()
            if success:
                messages.success(request, f"ML Model Retrained! {msg}")
            else:
                messages.warning(request, f"ML Model retraining error: {msg}")
        else:
            messages.error(request, "Only Admin can retrain model.")
        return redirect(f"{request.path}?date={target_date_str}&weather={weather}&is_holiday={'1' if is_holiday else '0'}&special_event={special_event}")

    predictions, reorder_recommendations = ml_engine.get_reorder_recommendations(
        target_date=target_date_str,
        weather=weather,
        is_holiday=is_holiday,
        special_event=special_event
    )

    # Actual vs Predicted comparison if historical date selected
    actual_records = SalesRecord.objects.filter(date=target_date).select_related('menu_item')
    actual_dict = {r.menu_item.id: r.quantity_sold for r in actual_records}

    comparison_data = []
    for p in predictions:
        act = actual_dict.get(p['item_id'], None)
        diff = (p['predicted_demand'] - act) if act is not None else None
        comparison_data.append({
            'item_name': p['item_name'],
            'predicted': p['predicted_demand'],
            'actual': act if act is not None else 'N/A',
            'difference': diff if diff is not None else 'N/A'
        })

    # Prepare Chart Data
    item_names = [p['item_name'] for p in predictions]
    pred_values = [p['predicted_demand'] for p in predictions]

    context = {
        'target_date_str': target_date_str,
        'target_date_display': target_date.strftime("%A, %b %d, %Y"),
        'weather': weather,
        'is_holiday': is_holiday,
        'special_event': special_event,
        'predictions': predictions,
        'comparison_data': comparison_data,
        'item_names_json': json.dumps(item_names),
        'pred_values_json': json.dumps(pred_values),
        'model_metrics': ml_engine.metrics,
        'is_admin': role_check_admin(request.user)
    }
    return render(request, 'inventory_predictor/prediction/predict.html', context)


# ==========================================
# 10. REORDER / STOCK RECOMMENDATIONS MODULE
# ==========================================
@login_required
def reorder_recommendations(request):
    target_date_str = request.GET.get('date', (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"))
    weather = request.GET.get('weather', 'Sunny')
    is_holiday = request.GET.get('is_holiday', '0') == '1'
    special_event = request.GET.get('special_event', 'None')

    predictions, recommendations = ml_engine.get_reorder_recommendations(
        target_date=target_date_str,
        weather=weather,
        is_holiday=is_holiday,
        special_event=special_event
    )

    reorder_required_count = sum(1 for r in recommendations if r['status'] == 'Reorder Required')
    total_estimated_reorder_cost = sum(r['estimated_cost'] for r in recommendations)

    context = {
        'target_date_str': target_date_str,
        'target_date_display': datetime.strptime(target_date_str, "%Y-%m-%d").strftime("%A, %b %d, %Y") if isinstance(target_date_str, str) else target_date_str,
        'recommendations': recommendations,
        'reorder_required_count': reorder_required_count,
        'total_estimated_reorder_cost': round(total_estimated_reorder_cost, 2),
        'weather': weather,
        'is_holiday': is_holiday,
        'special_event': special_event,
    }
    return render(request, 'inventory_predictor/reorders/recommendations.html', context)


# ==========================================
# 11. REPORTS MODULE
# ==========================================
@login_required
def reports_view(request):
    report_type = request.GET.get('type', 'inventory')
    start_date_str = request.GET.get('start_date', (date.today() - timedelta(days=30)).strftime("%Y-%m-%d"))
    end_date_str = request.GET.get('end_date', date.today().strftime("%Y-%m-%d"))

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except Exception:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

    report_data = []

    if report_type == 'inventory':
        report_data = Ingredient.objects.select_related('supplier').all()
    elif report_type == 'low_stock':
        report_data = [i for i in Ingredient.objects.select_related('supplier').all() if i.is_low_stock]
    elif report_type == 'expiring':
        report_data = [i for i in Ingredient.objects.select_related('supplier').all() if i.is_expiring_soon]
    elif report_type == 'usage':
        report_data = InventoryTransaction.objects.filter(
            transaction_type='USAGE',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('ingredient', 'performed_by').order_by('-created_at')
    elif report_type == 'wastage':
        report_data = Wastage.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('ingredient', 'reported_by').order_by('-date')
    elif report_type == 'sales':
        report_data = SalesRecord.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('menu_item').order_by('-date')

    context = {
        'report_type': report_type,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'report_data': report_data,
        'today': date.today()
    }
    return render(request, 'inventory_predictor/reports/reports.html', context)


# ==========================================
# 12. ANALYTICS MODULE
# ==========================================
@login_required
def analytics_view(request):
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # 1. Daily Sales Trend (30 days)
    sales_trend = SalesRecord.objects.filter(date__gte=thirty_days_ago)\
        .values('date')\
        .annotate(total_qty=Sum('quantity_sold'))\
        .order_by('date')

    sales_dates = [s['date'].strftime('%b %d') for s in sales_trend]
    sales_qtys = [s['total_qty'] for s in sales_trend]

    # 2. Category Share
    category_data = SalesRecord.objects.filter(date__gte=thirty_days_ago)\
        .values('menu_item__category')\
        .annotate(total_qty=Sum('quantity_sold'))\
        .order_by('-total_qty')

    cat_labels = [c['menu_item__category'] for c in category_data]
    cat_values = [c['total_qty'] for c in category_data]

    # 3. Wastage Reasons Breakdown
    wastage_data = Wastage.objects.values('reason')\
        .annotate(total_cost=Sum('estimated_cost'))\
        .order_by('-total_cost')

    wastage_labels = [w['reason'] for w in wastage_data]
    wastage_values = [float(w['total_cost']) for w in wastage_data]

    # 4. Top 5 High Usage Ingredients
    usage_data = InventoryTransaction.objects.filter(transaction_type='USAGE')\
        .values('ingredient__name')\
        .annotate(total_used=Sum('quantity'))\
        .order_by('-total_used')[:6]

    usage_labels = [u['ingredient__name'] for u in usage_data]
    usage_values = [u['total_used'] for u in usage_data]

    context = {
        'sales_dates_json': json.dumps(sales_dates),
        'sales_qtys_json': json.dumps(sales_qtys),
        'cat_labels_json': json.dumps(cat_labels),
        'cat_values_json': json.dumps(cat_values),
        'wastage_labels_json': json.dumps(wastage_labels),
        'wastage_values_json': json.dumps(wastage_values),
        'usage_labels_json': json.dumps(usage_labels),
        'usage_values_json': json.dumps(usage_values),
    }
    return render(request, 'inventory_predictor/analytics/analytics.html', context)


# ==========================================
# 13. USER MANAGEMENT MODULE (ADMIN)
# ==========================================
@login_required
def user_list(request):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied. Only Admin can manage users.")
        return redirect('dashboard')

    users = User.objects.select_related('profile').all()
    return render(request, 'inventory_predictor/users/list.html', {'users': users})


@login_required
def user_add(request):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserManagementForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                messages.error(request, f"User with username '{username}' already exists.")
            else:
                user = User.objects.create_user(
                    username=username,
                    password=form.cleaned_data['password'],
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )
                role = form.cleaned_data['role']
                phone = form.cleaned_data['phone']
                UserProfile.objects.create(user=user, role=role, phone=phone)

                if role == 'ADMIN':
                    user.is_staff = True
                    user.save()

                messages.success(request, f"User '{user.username}' created successfully as {role}!")
                return redirect('user_list')
    else:
        form = UserManagementForm()

    return render(request, 'inventory_predictor/users/form.html', {'form': form})


@login_required
def user_toggle_role(request, pk):
    if not role_check_admin(request.user):
        messages.error(request, "Access Denied.")
        return redirect('dashboard')

    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot modify your own role!")
        return redirect('user_list')

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.role == 'ADMIN':
        profile.role = 'STAFF'
        user.is_staff = False
    else:
        profile.role = 'ADMIN'
        user.is_staff = True

    profile.save()
    user.save()
    messages.success(request, f"Updated role for {user.username} to {profile.get_role_display()}")
    return redirect('user_list')
