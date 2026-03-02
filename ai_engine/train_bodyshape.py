import argparse
import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

def main(csv_path, out_path):
    df = pd.read_csv(csv_path)
    X = df[["shoulder_ratio", "waist_ratio", "hip_ratio", "leg_ratio"]].values
    y = df["label"].astype(str).values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=300, max_depth=6, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump(clf, f)
    print(f"Saved model to: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="datasets/bodyshape/ratios.csv")
    parser.add_argument("--out", default="backend/app/ai/bodyshape_rf.pkl")
    args = parser.parse_args()
    main(args.csv, args.out)
