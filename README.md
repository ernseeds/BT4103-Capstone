# BT4103 Capstone Project: Singapore Car Resale Price Prediction

## Overview

This capstone project develops a comprehensive web application for predicting resale prices of cars in Singapore. The system combines machine learning models with an interactive dashboard to provide accurate price predictions, market insights, and data analytics for car buyers and sellers.

## Features

### 🔮 Price Prediction
- **Machine Learning Models**: XGBoost, Random Forest, LightGBM, Linear Regression, and Lasso Regression
- **Feature Engineering**: Includes OMV, vehicle age, mileage, COE details, engine specifications, and more
- **SHAP Explanations**: Provides interpretable explanations for price predictions
- **Real-time Predictions**: FastAPI backend for instant price estimates

### 📊 Interactive Dashboard
- **Market Analytics**: Charts and visualizations for car market trends
- **COE Analysis**: Certificate of Entitlement bidding data and predictions
- **Brand/Make Insights**: Ownership trends, market share, and pricing patterns
- **Demand Forecasting**: Time-series analysis of car sales and prices

### 🌐 Web Application
- **Vue.js Frontend**: Modern, responsive UI built with Ant Design Vue
- **FastAPI Backend**: High-performance Python API with CORS support
- **Data Integration**: Google BigQuery for large-scale data processing
- **Docker Support**: Containerized deployment ready

### 🤖 Data Processing
- **BigQuery Integration**: Direct connection to Google Cloud BigQuery
- **ETL Pipelines**: Data extraction, transformation, and loading
- **Preprocessing**: Automated feature engineering and data cleaning

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI**: Modern, fast web framework
- **Pandas & NumPy**: Data manipulation
- **Scikit-learn**: Machine learning preprocessing
- **XGBoost**: Primary prediction model
- **SHAP**: Model interpretability
- **Google Cloud**: BigQuery, Storage, Authentication

### Frontend
- **Vue.js 2.6**: Progressive JavaScript framework
- **Ant Design Vue**: Enterprise UI components
- **Chart.js**: Data visualization
- **Axios**: HTTP client
- **Vue Router**: Single-page application routing

### Machine Learning
- **XGBoost**: Gradient boosting framework
- **LightGBM**: Microsoft's gradient boosting
- **Random Forest**: Ensemble learning
- **Linear/Lasso Regression**: Baseline models

### Infrastructure
- **Docker**: Containerization
- **Google Cloud Platform**: Data storage and processing
- **Firebase**: Hosting and deployment

## Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 16+
- Docker (optional)
- Google Cloud credentials

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/BT4103-Capstone.git
   cd BT4103-Capstone/Web Application/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Cloud credentials**
   - Place your service account JSON file in the backend directory
   - Update credentials path in relevant scripts

4. **Run the backend**
   ```bash
   python app.py
   # or with uvicorn
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd ../frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Run development server**
   ```bash
   npm run serve
   ```

4. **Build for production**
   ```bash
   npm run build
   ```

### Docker Deployment

```bash
# Backend
cd Web Application/backend
docker build -t car-price-backend .
docker run -p 8000:8000 car-price-backend

# Frontend
cd ../frontend
docker build -t car-price-frontend .
docker run -p 8080:8080 car-price-frontend
```

## Project Structure

```
BT4103-Capstone/
├── Price Prediction Models/     # Jupyter notebooks for ML models
│   ├── XGBoost.ipynb
│   ├── Random Forest.ipynb
│   ├── LightGBM.ipynb
│   └── Linear & Lasso Regression.ipynb
├── Web Application/
│   ├── backend/
│   │   ├── app.py              # FastAPI application
│   │   ├── landscanner.py      # Data processing utilities
│   │   ├── price_prediction/   # ML model and explainer
│   │   └── requirements.txt
│   └── frontend/
│       ├── src/
│       │   ├── views/          # Vue.js pages
│       │   ├── components/     # Reusable components
│       │   └── lib/            # API utilities
│       └── package.json
├── Forecasting/                 # Time series forecasting (future)
├── DAG/                        # Workflow orchestration (future)
└── README.md
```


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Creative Tim**: Muse Vue Ant Design Dashboard template
- **Google Cloud**: BigQuery and Cloud Storage
- **Singapore Land Transport Authority**: COE data
- **Car listing websites**: Data sources for market analysis

## Contact

For questions or support, please open an issue on GitHub or contact the development team.
