from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import pickle

# Initialize the Flask app
app = Flask(__name__)

# Basic config for auth and database
app.config['SECRET_KEY'] = 'replace-with-a-secure-random-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(150), nullable=True)
    model = db.Column(db.String(150), nullable=False)
    battery_capacity = db.Column(db.Float, nullable=False)
    charging_port_type = db.Column(db.String(100), nullable=False)

    owner = db.relationship('User', backref=db.backref('vehicles', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Load model, scaler, and encoder
with open("D:\Smart_charging_timePrediction_Optimization\SmartCharge-Pro-Smart-EV-Charging-Prediction-Optimization\models\ev_charging_model.pkl", "rb") as f:
    model = pickle.load(f)

with open("D:\Smart_charging_timePrediction_Optimization\SmartCharge-Pro-Smart-EV-Charging-Prediction-Optimization\models\scaler.pkl", "rb") as f:
    scaler = pickle.load(f)

with open("D:\Smart_charging_timePrediction_Optimization\SmartCharge-Pro-Smart-EV-Charging-Prediction-Optimization\models\encoder.pkl", "rb") as f:
    encoder = pickle.load(f)

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash('Please fill out all fields', 'warning')
            return redirect(url_for('register'))

        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            flash('User with that username or email already exists', 'warning')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('postlogin'))
        flash('Invalid username or password', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('index'))


# Define the home page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route('/postlogin')
@login_required
def postlogin():
    return render_template('postlogin.html')


@app.route('/how')
def how():
    return render_template('how.html')


@app.route('/vehicles')
@login_required
def vehicles():
    user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('vehicles.html', vehicles=user_vehicles)


@app.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        name = request.form.get('name')
        model_name = request.form.get('model')
        battery_capacity = request.form.get('battery_capacity')
        port_type = request.form.get('charging_port_type')
        try:
            battery_capacity = float(battery_capacity)
        except Exception:
            flash('Invalid battery capacity', 'warning')
            return redirect(url_for('add_vehicle'))

        v = Vehicle(user_id=current_user.id, name=name, model=model_name, battery_capacity=battery_capacity, charging_port_type=port_type)
        db.session.add(v)
        db.session.commit()
        flash('Vehicle added', 'success')
        return redirect(url_for('vehicles'))

    return render_template('vehicle_form.html', action='Add', vehicle=None)


@app.route('/vehicles/edit/<int:vid>', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vid):
    vehicle = Vehicle.query.get_or_404(vid)
    if vehicle.user_id != current_user.id:
        flash('Not authorized', 'danger')
        return redirect(url_for('vehicles'))

    if request.method == 'POST':
        vehicle.name = request.form.get('name')
        vehicle.model = request.form.get('model')
        try:
            vehicle.battery_capacity = float(request.form.get('battery_capacity'))
        except Exception:
            flash('Invalid battery capacity', 'warning')
            return redirect(url_for('edit_vehicle', vid=vid))
        vehicle.charging_port_type = request.form.get('charging_port_type')
        db.session.commit()
        flash('Vehicle updated', 'success')
        return redirect(url_for('vehicles'))

    return render_template('vehicle_form.html', action='Edit', vehicle=vehicle)


@app.route('/vehicles/delete/<int:vid>', methods=['POST'])
@login_required
def delete_vehicle(vid):
    vehicle = Vehicle.query.get_or_404(vid)
    if vehicle.user_id != current_user.id:
        flash('Not authorized', 'danger')
        return redirect(url_for('vehicles'))
    db.session.delete(vehicle)
    db.session.commit()
    flash('Vehicle deleted', 'info')
    return redirect(url_for('vehicles'))


@app.route('/api/vehicle/<int:vid>')
@login_required
def api_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    if v.user_id != current_user.id:
        return jsonify({'error': 'not authorized'}), 403
    return jsonify({
        'id': v.id,
        'name': v.name,
        'model': v.model,
        'battery_capacity': v.battery_capacity,
        'charging_port_type': v.charging_port_type
    })

# Define the prediction route (GET shows form, POST computes)
@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if request.method == 'GET':
        user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
        return render_template('predict.html', vehicles=user_vehicles)

    try:
        # Get user input from the request
        battery_capacity = float(request.form.get("battery_capacity"))
        current_battery = float(request.form.get("current_battery"))
        charging_power = float(request.form.get("charging_power"))
        temperature = float(request.form.get("temperature"))
        charging_type = request.form.get("charging_type")

        # Create a DataFrame with user input
        input_data = pd.DataFrame([[battery_capacity, current_battery, charging_power, temperature, charging_type]],
                                  columns=['battery_capacity', 'current_battery_level', 'charging_power', 'temperature', 'charging_station_type'])

        # One-hot encode the 'charging_station_type' column
        encoded_type = encoder.transform(input_data[['charging_station_type']])
        encoded_df = pd.DataFrame(encoded_type, columns=encoder.get_feature_names_out(['charging_station_type']))

        # Drop the original 'charging_station_type' and join the encoded columns
        input_data = input_data.drop(columns=['charging_station_type']).join(encoded_df)

        # Scale the numerical features
        input_data.iloc[:, :-1] = scaler.transform(input_data.iloc[:, :-1])

        # Make the prediction
        prediction = model.predict(input_data)

        # Convert the prediction to a standard Python float (this ensures it's JSON serializable)
        prediction_value = float(prediction[0])

        # Add optimization suggestions
        optimization_suggestions = get_optimization_suggestions(battery_capacity, current_battery, charging_power, temperature, charging_type, prediction_value)

        return render_template("result.html", prediction=round(prediction_value, 2), suggestions=optimization_suggestions)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

def get_optimization_suggestions(battery_capacity, current_battery, charging_power, temperature, charging_type, predicted_time):
    suggestions = []

    # Optimization Tips Based on Predicted Charging Time (in minutes)
    if predicted_time < 15:
        suggestions.append("Charging time is quick, but make sure your battery is not being overcharged.")
        if charging_power < 50:
            suggestions.append("Consider using a DC Fast Charger to further reduce charging time.")
        if charging_type == 'AC_Slow':
            suggestions.append("AC Slow chargers are fine but consider upgrading to DC for quicker charging.")
    elif 15 <= predicted_time < 45:
        suggestions.append("You can optimize the charging time by considering the time of day. Charge during off-peak hours to reduce power grid congestion.")
        if charging_power < 100:
            suggestions.append("Increase charging power if possible, but ensure the charger supports it.")
        if temperature < 5 or temperature > 35:
            suggestions.append("Charging is slower in extreme temperatures. Try to charge within a more moderate temperature range.")
        if charging_type == 'AC_Slow':
            suggestions.append("Switch to DC Fast Charger for reducing charging time in urgent situations.")
    elif 45 <= predicted_time < 75:
        suggestions.append("You may want to charge overnight or during extended periods when you're not in a rush.")
        if charging_power < 50:
            suggestions.append("Switching to a DC Fast Charger could drastically reduce your charging time.")
        if charging_type == 'AC_Slow':
            suggestions.append("AC Slow charging can work fine for regular use but is not ideal when you need to save time.")
        if temperature < 5 or temperature > 35:
            suggestions.append("Extreme temperatures are affecting charging efficiency. Try to charge in optimal temperature conditions (between 20-25°C).")
    elif predicted_time >= 75:
        suggestions.append("For very long charging times, plan ahead and charge during the night or when you're not in a rush.")
        if charging_power < 100:
            suggestions.append("Consider upgrading to a higher-power charger to speed up the charging process.")
        if current_battery < 20:
            suggestions.append("Low battery levels will naturally take longer to charge. Consider starting charging earlier in the day to avoid delays.")
        if charging_type == 'AC_Slow':
            suggestions.append("AC Slow charging is too slow for such high charging times. Switch to DC Fast Charging if you're in a hurry.")
        if temperature < 5 or temperature > 35:
            suggestions.append("Charging will be significantly slower in extreme temperatures. Charge in moderate temperature conditions for better efficiency.")

    if charging_power < 50:
        suggestions.append("Consider using a DC Fast Charger for faster charging.")
    if current_battery < 20:
        suggestions.append("Charging from low battery levels may take longer. Charge early when possible.")
    if charging_type == 'AC_Slow':
        suggestions.append("AC Slow chargers are better for long-term, non-time-sensitive charging.")
    if temperature < 5 or temperature > 35:
        suggestions.append("Charging efficiency is lower in extreme temperatures. Avoid charging in very hot or cold conditions.")

    return suggestions

# Run the Flask app
if __name__ == "__main__":
    # Create DB tables if they don't exist (safe for dev)
    with app.app_context():
        db.create_all()

    app.run(debug=True)
