# authors: Cal Schafer, Daniel Ortiz, Jordan Lau, William Xu
# date: 2020-11-26

"""Prediction of Housing Prices using RidgeRegression, RandomForestRegressor, and XGBRegressor

Usage: data_analysis.py --in_file1=<in_file1> --in_file2=<in_file2> \
                        --out_file1=<out_file1> --out_file2=<out_file2> --out_file3=<out_file3>
 
Options:

--in_file1=<in_file1>        file path of the input cleaned train set
--in_file2=<in_file2>        file path of the input cleaned test set
--out_file1=<out_file1>      file path for a table of cross validation scores
--out_file2=<out_file2>      file path for a table of model scoring on testing data
--out_file3=<out_file3>      file path for a table of estimated coefficients from the model 
"""

import os
import pandas as pd
import numpy as np
from docopt import docopt
from sklearn.compose import (
    ColumnTransformer,
    TransformedTargetRegressor,
    make_column_transformer,
)
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.model_selection import (
    cross_validate,
    train_test_split,
)
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.metrics import r2_score
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

opt = docopt(__doc__)

def main(in_file1,in_file2, out_file1, out_file2, out_file3):

    train_df = pd.read_csv(in_file1)
    test_df = pd.read_csv(in_file2)
    
    #take in csv file from script2: data_cleaning 
    X_train, y_train = train_df[["AGE", "BLDG_DESC", "BLDG_FEET", "GARAGE", "FIREPLACE", "BASEMENT", "BSMTDEVL", "LATITUDE", "LONGITUDE"]], train_df['ASSESSMENT']
    X_test, y_test = test_df[["AGE", "BLDG_DESC", "BLDG_FEET", "GARAGE", "FIREPLACE", "BASEMENT", "BSMTDEVL", "LATITUDE", "LONGITUDE"]], test_df['ASSESSMENT']
    
    #define feature types
    categorical_features = ["BLDG_DESC"]
    binary_features = ["GARAGE", "FIREPLACE", "BASEMENT", "BSMTDEVL"]
    numerical_features = ["AGE", "BLDG_FEET", "LATITUDE", "LONGITUDE"]
    
    #dictionary to store scores
    store_scores = {}
    
    #Baseline DummyRegressor 
    dummy = DummyRegressor()
    dummy_scores = cross_validate(dummy, X_train, y_train, return_train_score=True, scoring = "r2")
    store_scores = {"dummy_score": pd.DataFrame(dummy_scores).mean().round(4).tolist()}
    
    #Data transformation and preprocessor pipelines 
    categorical_transformer = make_pipeline(
        SimpleImputer(strategy = "constant"),
        OneHotEncoder(handle_unknown="ignore"),
    )
    
    binary_transformer = make_pipeline(
        OneHotEncoder(drop="if_binary", dtype=int),    
    )
    
    numerical_transformer = make_pipeline(
        SimpleImputer(strategy = "constant"),
    )
    
    preprocessor = make_column_transformer(
        (categorical_transformer, categorical_features),
        (binary_transformer, binary_features),
        (numerical_transformer, numerical_features),
    )
    
    #Ridge regression and hyperparamter tuning using RidgeCV
    alphas = 10.0**np.arange(-5,5,1)
    ridgecv = make_pipeline(preprocessor, RidgeCV(alphas=alphas))
    ridgecv_scores = cross_validate(ridgecv, X_train, y_train, cv=10, return_train_score=True, scoring = "r2")
    store_scores["ridgecv_score"] =  pd.DataFrame(ridgecv_scores).mean().round(4).tolist()
    
    #RandomForestRegressor() with max_depth = , n_estimators = 70, and random_state= 123
    random_forest_regression = make_pipeline(preprocessor, RandomForestRegressor(max_depth = 5, n_estimators= 70, random_state=123))
    random_forest_scores = cross_validate(random_forest_regression, X_train, y_train, cv=5, return_train_score=True, scoring= 'r2', n_jobs=-1)
    store_scores["random_forest"] = pd.DataFrame(random_forest_scores).mean().round(4).tolist()
    
    #XGBRegressor() with max_depth = , n_estimators = 70, and random_state= 123
    xgb_regression = make_pipeline(preprocessor, XGBRegressor(max_depth = 5, n_estimators= 70, random_state=123))
    xgb_scores = cross_validate(xgb_regression, X_train, y_train, cv=5, return_train_score=True, scoring= 'r2', n_jobs=-1)
    store_scores["XGB_Regression"] = pd.DataFrame(xgb_scores).mean().round(4).tolist()

    #table for cross_validation scores 
    scores_df = pd.DataFrame(store_scores, index = dummy_scores.keys())
    scores_df.reset_index(inplace=True)
    
    #test_score
    ridgecv.fit(X_train, y_train);
    test_score = r2_score(y_test, ridgecv.predict(X_test))
    test_set_score = pd.DataFrame(test_score,
                  index=["test_score"],
                  columns=['RidgeCV'])
    test_set_score.reset_index(inplace=True)
    
    #Get list of features created from preprocessor step for each type of data 
    ohe_columns = list(preprocessor.named_transformers_['pipeline-1'].named_steps['onehotencoder'].get_feature_names(categorical_features))
    binary_columns = list(preprocessor.named_transformers_['pipeline-2'].named_steps['onehotencoder'].get_feature_names(binary_features))
    features = ohe_columns + binary_columns + numerical_features
    
    #Weights of coefficients
    weights = ridgecv.named_steps['ridgecv'].coef_.round(2).flatten()
    inds = np.argsort(ridgecv.named_steps['ridgecv'].coef_.flatten())
    feature_table = {"feature": [features[index] for index in inds[:]], "coefficient": [weights[index] for index in inds[:]]}
    feature_table = pd.DataFrame(feature_table)
    
    
    # produce output files and create directory if it does not exist
    try:
        scores_df.to_csv(out_file1, index=False)
    except:
        os.makedirs(os.path.dirname(out_file1))
        scores_df.to_csv(out_file1, index=False)
        
    try:
        test_set_score.to_csv(out_file2, index=False)
    except:
        os.makedirs(os.path.dirname(out_file2))
        test_set_score.to_csv(out_file2, index=False)
        
    try:
        feature_table.to_csv(out_file3, index=False)
    except:
        os.makedirs(os.path.dirname(out_file3))
        feature_table.to_csv(out_file3, index=False)
        

if __name__ == "__main__":
    main(opt["--in_file1"], opt["--in_file2"], opt["--out_file1"], opt["--out_file2"], opt["--out_file3"])
