import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Load preprocessed data
df = pd.read_csv("D:\Smart_charging_timePrediction_Optimization\SmartCharge-Pro-Smart-EV-Charging-Prediction-Optimization\dataset\preprocessed_data.csv")

# Splitting dataset
X = df.drop(columns=['charging_time_minutes'])
y = df['charging_time_minutes']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train optimized XGBoost model
model = XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=6, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
accuracy = r2 * 100
print(f"MAE: {mae:.2f}, R2 Score: {r2:.2f}, Accuracy: {accuracy:.2f}%")

# Save model
with open("D:\Smart_charging_timePrediction_Optimization\SmartCharge-Pro-Smart-EV-Charging-Prediction-Optimization\models\ev_charging_model.pkl", "wb") as f:
    pickle.dump(model, f)
