# Cloud Kitchen Inventory and Demand Prediction System

A complete web-based web application developed in **Python Django** for managing inventory in a cloud kitchen and predicting future demand for menu items using **Machine Learning (Scikit-Learn Random Forest Regressor)**.

---

## 📌 Project Objective
Cloud kitchens face significant challenges regarding raw ingredient overstocking, stockouts during peak ordering hours, food spoilage/wastage, and inefficient procurement planning. 

This system provides:
1. **Real-time Inventory Tracking:** Monitors ingredients, current stock, safety thresholds, unit costs, and expiry dates.
2. **Machine Learning Demand Prediction:** Predicts expected order volumes per dish based on historical sales data, day-of-week trends, weather conditions, public holidays, and promotional events.
3. **Automated Reorder Recommendations:** Calculates total raw ingredient requirements by mapping dish demand predictions to dish recipe Bill of Materials (BOM). Highlights stock shortfalls and suggests optimal purchase order quantities.
4. **Wastage & Spoilage Logging:** Tracks wasted ingredients with cause breakdown (Expired, Spoiled, Over-preparation) and financial impact.
5. **Role-Based Access Control:** Separate features for **Admin / Kitchen Managers** and **Kitchen Staff**.
6. **Analytics & Reports:** Interactive Chart.js visual charts and filterable reports.

---

## 🛠️ Technology Stack
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, FontAwesome 6
- **Backend:** Python 3.10+, Django 5.x
- **Database:** SQLite3
- **Data Processing:** Pandas, NumPy
- **Machine Learning:** Scikit-Learn (`RandomForestRegressor`)
- **Visualizations:** Chart.js
- **Authentication:** Django Authentication & Role-Based User Profiles

---

## 📁 Project Structure

```text
newkp/
│
├── manage.py                        # Django project manager script
├── db.sqlite3                       # Pre-seeded SQLite database
├── README.md                        # Documentation & setup guide
│
├── cloud_kitchen_proj/              # Main Django Configuration Package
│   ├── __init__.py
│   ├── settings.py                  # Project settings, database & app registry
│   ├── urls.py                      # Root URL routing
│   ├── wsgi.py
│   └── asgi.py
│
└── inventory_predictor/             # Primary Core Application App
    ├── admin.py                     # Django Admin registration for all 9 models
    ├── apps.py
    ├── forms.py                     # Django forms for Ingredients, Menu, Wastage, Sales
    ├── ml_engine.py                 # Scikit-Learn ML demand forecasting & reorder calculation
    ├── models.py                    # Database schema (9 models)
    ├── urls.py                      # Application URL routes
    ├── views.py                     # Business logic & view functions
    │
    ├── management/
    │   └── commands/
    │       └── seed_data.py         # Management command: `python manage.py seed_data`
    │
    ├── static/
    │   ├── css/
    │   │   └── style.css            # Custom responsive dashboard & sidebar CSS
    │   └── js/
    │       └── main.js             # UI scripts & alert auto-dismiss
    │
    └── templates/
        └── inventory_predictor/     # HTML5 Responsive Templates
            ├── base.html            # Master layout template (Sidebar, Topbar, Footer)
            ├── login.html           # Authentication login page
            ├── dashboard.html       # KPI Cards, Chart.js trends, Alerts table
            ├── confirm_delete.html  # Generic confirmation modal
            ├── ingredients/
            │   ├── list.html        # Ingredient inventory list with low stock/expiry badges
            │   └── form.html        # Add / Edit ingredient form
            ├── menu/
            │   ├── list.html        # Menu catalogue
            │   ├── form.html        # Add / Edit dish form
            │   └── recipe.html      # Recipe Bill of Materials (BOM) ingredient mapping
            ├── suppliers/
            │   ├── list.html        # Approved supplier directory
            │   └── form.html        # Add / Edit supplier form
            ├── inventory/
            │   ├── status.html      # Stock valuation & quick actions
            │   ├── add_stock.html   # Inward stock purchase entry
            │   ├── record_usage.html# Outward kitchen usage entry
            │   └── transactions.html# Audit trail transaction log
            ├── wastage/
            │   ├── list.html        # Food wastage log & total cost summary
            │   └── form.html        # Record spoilage/wastage form
            ├── sales/
            │   ├── list.html        # Historical sales & environmental dataset
            │   └── form.html        # Record daily sales data form
            ├── prediction/
            │   └── predict.html     # ML forecast simulation, metrics & actual vs predicted
            ├── reorders/
            │   └── recommendations.html # AI Stock Reorder analysis & shortfall calculation
            ├── reports/
            │   └── reports.html     # Filterable & printable audit reports
            ├── analytics/
            │   └── analytics.html   # Visual Chart.js dashboards
            └── users/
                ├── list.html        # User account role management (Admin only)
                └── form.html        # Add user account form
```

---

## 🗄️ Database Schema & Models

1. **`UserProfile`:** Extends Django `User` with roles (`ADMIN`, `STAFF`) and phone number.
2. **`Supplier`:** Stores vendor company name, contact person, phone, email, and address.
3. **`Ingredient`:** Raw materials with category, unit, current quantity, min/max thresholds, unit cost, supplier, and expiry date.
4. **`MenuItem`:** Menu dishes with category, selling price, availability status, and description.
5. **`MenuItemIngredient`:** Junction table defining dish recipe requirements (e.g., 1 Chicken Burger = 0.15 kg Chicken + 1 Bun + 1 Cheese slice).
6. **`InventoryTransaction`:** Logs stock movements (`PURCHASE`, `USAGE`, `WASTAGE`, `ADJUSTMENT`).
7. **`Wastage`:** Tracks spoiled/expired food quantity, reason, date, and calculated cost.
8. **`SalesRecord`:** Historical demand dataset storing Date, Menu Item, Quantity Sold, Day of Week, Month, Holiday Flag, Weather, and Special Event.
9. **`DemandPrediction`:** Stores ML predicted demand vs actual sales for model validation.

---

## 🧠 Machine Learning Demand Prediction Architecture

The prediction module (`ml_engine.py`) uses **Scikit-Learn's RandomForestRegressor**:
- **Features ($X$):**
  - `menu_item_id` (Dish identifier)
  - `day_of_week` (0=Monday to 6=Sunday)
  - `month` (1 to 12)
  - `is_holiday` (0 or 1)
  - `weather_code` (Sunny=0, Rainy=1, Cloudy=2, Windy=3)
  - `event_code` (None=0, Festival=1, Sports Match=2, Weekend Promo=3)
- **Target ($y$):** `quantity_sold`
- **Reorder Calculation Algorithm:**
  $$\text{Required Ingredient Stock} = \sum_{\text{Dishes}} (\text{Predicted Demand} \times \text{Ingredient Qty Per Dish})$$
  $$\text{Shortfall} = \text{Required Ingredient Stock} - \text{Current Stock}$$
  $$\text{Suggested Reorder Qty} = \max(0, \text{Shortfall} + \text{Min Stock Level})$$

---

## 🔑 Default Login Credentials

The project comes pre-loaded with sample data and ready-to-use user accounts:

| User Role | Username | Password | Access Privileges |
| :--- | :--- | :--- | :--- |
| **Admin / Kitchen Manager** | `admin` | `admin123` | Full control: CRUD ingredients, dishes, suppliers, users, retrain ML model, record transactions & wastage. |
| **Kitchen Staff** | `staff` | `staff123` | Operational access: View stock, record kitchen usage, log food wastage, view demand predictions. |

---

## 🚀 Quickstart & How to Run

### Step 1: Clone or Open Project Directory
Navigate to the project root directory in your command prompt / terminal:
```bash
cd c:\Users\91623\Downloads\newkp
```

### Step 2: Install Python Dependencies (If not already installed)
```bash
pip install django pandas numpy scikit-learn
```

### Step 3: Database Migration & Seeding (Already Pre-Seeded)
To re-seed or populate fresh sample data at any time:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_data
```

### Step 4: Run Development Server
```bash
python manage.py runserver
```

### Step 5: Open Application in Web Browser
Open your browser and navigate to:
```text
http://127.0.0.1:8000/
```

---

## 🎬 MCA Mini Project Demonstration Walkthrough

When presenting this project for your MCA Viva / Demo:

1. **Login:** Log in as `admin` (`admin123`). Show the role badge at the bottom of the sidebar.
2. **Dashboard Overview:** Point out the KPI cards (Total Ingredients, Low Stock Warnings, Expiring Soon, Today's Sales, Tomorrow's Predicted Demand), 14-day sales trend chart, and top-selling dishes.
3. **Ingredient Management:** Go to **Ingredients Stock**. Filter by "Low Stock Only". Show how red badges highlight items below minimum safety levels. Click "Add New Ingredient".
4. **Menu & Recipe Management:** Go to **Menu Items & Recipe**. Show how dishes have defined ingredient recipes (e.g. Classic Chicken Burger requires Chicken, Buns, Cheese, Tomatoes). Click "Recipe" to show adding or removing recipe ingredients.
5. **Record Stock Transactions:** Go to **Stock Transactions**. Demonstrate adding inward stock purchase or recording kitchen usage, showing automatic deduction of current quantity.
6. **Log Food Wastage:** Go to **Wastage Management**. Record 1 kg of spoiled Tomatoes due to "Spoiled". Show how stock decreases automatically and total financial loss is updated.
7. **Demand Prediction Simulation:** Go to **Demand Prediction**. Change the forecast date, select "Rainy" weather and "IPL / Sports Match" special event. Click "Generate AI Demand Prediction". Observe how predicted orders increase realistically for delivery-heavy items. Show the ML metrics box ($R^2$ score and MAE).
8. **Stock Reorder Recommendations:** Go to **Stock Recommendations**. Show how the system converts dish predictions into raw ingredient requirements, detects shortfalls against current inventory, marks status as **"Reorder Required"**, and calculates approximate required order quantities and estimated procurement costs.
9. **Analytics & Reports:** Demonstrate the **Analytics** visual graphs and **Reports** module with printable output.
10. **Role-Based Access:** Log out and log in as `staff` (`staff123`). Show how admin-only management buttons (User management, supplier editing, ingredient deletion) are hidden or restricted.
