# BT4103 Capstone Project: Singapore Car Resale Price Prediction

## Overview

This capstone project focuses on developing machine learning models for predicting resale prices of cars in Singapore. The system leverages various ML algorithms to provide accurate price predictions, market insights, and data analytics for car buyers and sellers. It includes data processing pipelines, model training notebooks, and forecasting capabilities.

## Features

### 🔮 Price Prediction Models
- **Machine Learning Algorithms**: XGBoost, Random Forest, LightGBM, Linear Regression, and Lasso Regression
- **Feature Engineering**: Incorporates OMV, vehicle age, mileage, COE details, engine specifications, and more
- **Model Interpretability**: Uses SHAP for explaining price predictions
- **Model Comparison**: Jupyter notebooks for training and evaluating different models

### 📊 Data Processing and Analytics
- **ETL Pipelines**: Data extraction, transformation, and loading processes
- **Preprocessing**: Automated feature engineering and data cleaning
- **BigQuery Integration**: Direct connection to Google Cloud BigQuery for large-scale data processing

### 📈 Forecasting
- **Time-Series Analysis**: Forecasting car sales and price trends
- **Demand Prediction**: Analysis of market demand patterns

### 🔄 Workflow Orchestration
- **Airflow DAG**: Directed Acyclic Graphs for automating data workflows

## Tech Stack

### Machine Learning
- **Python 3.11+**
- **Jupyter Notebook**: For model development and experimentation
- **Pandas & NumPy**: Data manipulation and analysis
- **Scikit-learn**: Machine learning preprocessing and evaluation
- **XGBoost**: Gradient boosting framework
- **LightGBM**: Microsoft's gradient boosting library
- **Random Forest**: Ensemble learning method
- **Linear/Lasso Regression**: Baseline regression models
- **SHAP**: Model interpretability library

### Data Processing
- **Google Cloud BigQuery**: Large-scale data storage and querying
- **Google Cloud Storage**: Data storage solutions

### Infrastructure
- **Google Cloud Platform**: Cloud-based data processing and storage

## Installation & Setup

### Prerequisites
- Python 3.11+
- Jupyter Notebook or JupyterLab
- Google Cloud credentials (for BigQuery access)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ernseeds/BT4103-Capstone.git
   cd BT4103-Capstone
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   (Note: Ensure requirements.txt is present in the root or relevant directories)

3. **Set up Google Cloud credentials**
   - Obtain your service account JSON file from Google Cloud Console
   - Set the environment variable or place the file in the project directory
   - Update any scripts that require authentication

4. **Run Jupyter Notebooks**
   - Navigate to the `Price Prediction Models/` directory
   - Open and run the notebooks (e.g., XGBoost.ipynb, Random Forest.ipynb) in Jupyter
   - For forecasting, explore the `Forecasting/` directory
   - For ETL pipeline, check the `Airflow DAG/` directory

## Project Structure

```
BT4103-Capstone/
├── Price Prediction Models/     # Jupyter notebooks for ML models
│   ├── XGBoost.ipynb
│   ├── Random Forest.ipynb
│   ├── LightGBM.ipynb
│   ├── Linear & Lasso Regression.ipynb
│   └── xgb_price_prediction_model  # Saved model file
├── Forecasting/                 # Time series forecasting notebooks/scripts
├── Airflow DAG/                        # Workflow orchestration scripts
├── .gitignore
└── README.md
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Google Cloud**: BigQuery and Cloud Storage for data processing
- **Singapore Land Transport Authority**: COE data sources
- **Car listing websites**: Data sources for market analysis
- **Open-source ML libraries**: XGBoost, LightGBM, SHAP, etc.

## Contact

For questions or support, please open an issue on GitHub or contact the development team.
