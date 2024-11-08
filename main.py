from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import pandas as pd
import pickle
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import os
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Render provides this PORT variable
    uvicorn.run(app, host="0.0.0.0", port=port)

# Load the model and encoders
with open("user_preference_model2.pkl", "rb") as f:
    model_data = pickle.load(f)
model = model_data['model']
label_encoders = model_data['encoders']

# Define input data model for prediction
class PredictionInput(BaseModel):
    age: int
    gender: str
    region: str
    interest_tags: str
    avg_session_dur: float
    ctr: float
    pages_viewed: int

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    # Ensure the uploads directory exists
    os.makedirs("uploads", exist_ok=True)

    # Save the uploaded file
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())

    # Load dataset
    data = pd.read_csv(file_location)

    # Generate visualizations
    visualizations = generate_visualizations(data)

    return {"visualizations": visualizations}

def generate_visualizations(data):
    # Ensure the visualizations directory exists
    os.makedirs("visualizations", exist_ok=True)

    visualizations = []

    # Subscription Status Distribution (Bar Plot)
    plt.figure(figsize=(10, 5))
    subscription_counts = data['Subscription_Status'].value_counts()
    sns.barplot(x=subscription_counts.index, y=subscription_counts.values)
    plt.title("Subscription Status Distribution")
    plt.xlabel("Subscription Status")
    plt.ylabel("Count")
    plt.savefig("visualizations/subscription_status.png")
    visualizations.append("/visualizations/subscription_status.png")
    plt.close()

    # Subscription Status Distribution (Pie Chart)
    plt.figure(figsize=(8, 8))
    subscription_counts.plot.pie(autopct='%1.1f%%', startangle=140, colors=sns.color_palette("Set3"))
    plt.title("Subscription Status Proportion")
    plt.ylabel("")
    plt.savefig("visualizations/subscription_status_pie.png")
    visualizations.append("/visualizations/subscription_status_pie.png")
    plt.close()

    # Age Distribution
    plt.figure(figsize=(10, 5))
    sns.histplot(data['Age'], kde=True)
    plt.title("Age Distribution")
    plt.xlabel("Age")
    plt.savefig("visualizations/age_distribution.png")
    visualizations.append("/visualizations/age_distribution.png")
    plt.close()

    # Interest Tags Word Cloud
    interest_text = " ".join(data['Interest_Tags'].dropna())
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(interest_text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.savefig("visualizations/interest_tags_wordcloud.png")
    visualizations.append("/visualizations/interest_tags_wordcloud.png")
    plt.close()

    # Correlation Heatmap
    plt.figure(figsize=(12, 8))
    
    # Select only numeric columns
    numeric_data = data.select_dtypes(include=[float, int])  
    
    if not numeric_data.empty:  # Check if there are numeric columns
        correlation = numeric_data.corr()  # Calculate correlation only on numeric data
        sns.heatmap(correlation, annot=True, cmap="coolwarm", fmt=".2f", square=True)
        plt.title("Correlation Heatmap")
        plt.savefig("visualizations/correlation_heatmap.png")
        visualizations.append("/visualizations/correlation_heatmap.png")
    else:
        print("No numeric data available for correlation.")
    plt.close()

    return visualizations

# Static file serving
app.mount("/visualizations", StaticFiles(directory="visualizations"), name="visualizations")

# Prediction endpoint
@app.post("/predict/")
async def predict_subscription_status(input_data: PredictionInput):
    # Encode categorical inputs
    gender_encoded = label_encoders['Gender'].transform([input_data.gender])[0]
    region_encoded = label_encoders['Region'].transform([input_data.region])[0]
    interest_encoded = label_encoders['Interest_Tags'].transform([input_data.interest_tags])[0]

    # Prepare feature vector for prediction
    user_features = [[
        input_data.age,
        gender_encoded,
        region_encoded,
        interest_encoded,
        input_data.avg_session_dur,
        input_data.ctr,
        input_data.pages_viewed
    ]]

    # Make prediction
    prediction = model.predict(user_features)
    subscription_status = label_encoders['Subscription_Status'].inverse_transform(prediction)

    return JSONResponse(content={"predicted_subscription_status": subscription_status[0]})

# To run the app, use: uvicorn filename:app
