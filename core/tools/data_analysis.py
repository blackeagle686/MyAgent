import os
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Any, Dict, List, Optional, Union
from .base import BaseTool
from .code_security_decorator import safe_execution, timeout, audit_log

class DataAnalysisTool(BaseTool):
    """
    A comprehensive tool for data analysis and machine learning.
    Follows a modular pipeline: Loading -> Cleaning -> EDA -> Feature Engineering -> ML -> Evaluation.
    """
    name = "data_analysis"
    description = (
        "Performs data analysis and machine learning tasks. "
        "Enforces a modular pipeline: Loading, Cleaning, EDA (Plotly JSON), Feature Engineering, "
        "Splitting, Training, and Evaluation. Supports CSV, Excel, JSON, and SQL."
    )

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "enum": ["full_pipeline", "eda", "train_model", "predict"],
                        "description": "The task to perform."
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the data file."
                    },
                    "target_column": {
                        "type": "string",
                        "description": "The column to predict (for ML tasks)."
                    },
                    "ml_task": {
                        "type": "string",
                        "enum": ["classification", "regression", "clustering"],
                        "description": "Type of machine learning task."
                    },
                    "connection_string": {
                        "type": "string",
                        "description": "SQLAlchemy connection string for SQL tasks."
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query for SQL tasks."
                    }
                },
                "required": ["task", "file_path"]
            }
        }

    @safe_execution
    @timeout(seconds=60)
    @audit_log
    def execute(self, task: str, file_path: str, **kwargs) -> str:
        try:
            # 1. Loading Data
            df = self._load_data(file_path, kwargs.get("connection_string"), kwargs.get("query"))
            results = {"steps": []}

            # 2. Cleaning Data
            df, clean_info = self._clean_data(df)
            results["steps"].append({"name": "Cleaning", "info": clean_info})

            if task == "eda" or task == "full_pipeline":
                # 3. EDA & Visualization
                eda_results = self._eda(df)
                results["steps"].append({"name": "EDA", "data": eda_results})

            if task == "train_model" or task == "full_pipeline":
                target = kwargs.get("target_column")
                ml_task = kwargs.get("ml_task")
                
                if not target and ml_task != "clustering":
                    return "Error: target_column is required for supervised learning."
                
                # 4. Feature Engineering & 5. Splitting & 6. Training & 7. Evaluation
                ml_results = self._ml_pipeline(df, target, ml_task)
                results["steps"].append({"name": "ML_Pipeline", "data": ml_results})

            return json.dumps(results, indent=2, default=str)

        except Exception as e:
            return f"Error in data_analysis: {str(e)}"

    def _load_data(self, path: str, connection_string: str = None, query: str = None) -> pd.DataFrame:
        if connection_string and query:
            from sqlalchemy import create_engine
            engine = create_engine(connection_string)
            return pd.read_sql(query, engine)
        
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            return pd.read_csv(path)
        elif ext in [".xls", ".xlsx"]:
            return pd.read_excel(path)
        elif ext == ".json":
            return pd.read_json(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _clean_data(self, df: pd.DataFrame) -> (pd.DataFrame, dict):
        info = {
            "initial_shape": df.shape,
            "missing_before": df.isnull().sum().sum(),
        }
        # Simple cleaning: drop duplicates, fill numeric with mean, categorical with mode
        df = df.drop_duplicates()
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns
        for col in categorical_cols:
            df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "Unknown")
            
        info["final_shape"] = df.shape
        info["missing_after"] = df.isnull().sum().sum()
        return df, info

    def _eda(self, df: pd.DataFrame) -> dict:
        summary = df.describe(include='all').to_dict()
        
        # Create a sample visualization (correlation heatmap if enough numeric columns)
        numeric_df = df.select_dtypes(include=[np.number])
        viz_json = None
        if len(numeric_df.columns) >= 2:
            corr = numeric_df.corr()
            fig = px.imshow(corr, text_auto=True, title="Correlation Heatmap")
            viz_json = fig.to_dict() # Returning as dict (shapes on json type)

        return {
            "summary_statistics": summary,
            "visualization": viz_json
        }

    def _ml_pipeline(self, df: pd.DataFrame, target: str, ml_task: str) -> dict:
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import LabelEncoder, StandardScaler
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.cluster import KMeans
        from sklearn.metrics import accuracy_score, mean_squared_error, silhouette_score

        # Feature Engineering (Basic Encoding)
        le = LabelEncoder()
        df_encoded = df.copy()
        for col in df_encoded.select_dtypes(exclude=[np.number]).columns:
            df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))

        if ml_task == "clustering":
            X = df_encoded
            kmeans = KMeans(n_clusters=3, random_state=42, n_init='auto')
            clusters = kmeans.fit_predict(X)
            score = silhouette_score(X, clusters)
            
            # Visualization
            fig = px.scatter(X, x=X.columns[0], y=X.columns[1], color=clusters, title="Clustering Results")
            return {
                "task": "clustering",
                "silhouette_score": score,
                "visualization": fig.to_dict()
            }

        X = df_encoded.drop(columns=[target])
        y = df_encoded[target]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        if ml_task == "classification":
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            score = accuracy_score(y_test, preds)
            metric_name = "accuracy"
        elif ml_task == "regression":
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            score = mean_squared_error(y_test, preds)
            metric_name = "rmse" # We'll return RMSE (calculated after)
            score = np.sqrt(score)
        else:
            raise ValueError(f"Unknown ML task: {ml_task}")

        # Importance Plot
        importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
        fig = px.bar(importances, title="Feature Importance")
        
        return {
            "task": ml_task,
            metric_name: score,
            "visualization": fig.to_dict()
        }
