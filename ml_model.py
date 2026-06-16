import json
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report
)

import joblib

from config import (
    DATASET_PATH,
    MODELO_PATH,
    VECTORIZER_PATH,
    METRICAS_PATH
)

from utils import normalizar_texto


def entrenar_modelo():
    dataset = pd.read_csv(DATASET_PATH, sep=";")
    dataset.columns = dataset.columns.str.strip()

    textos = dataset["texto"].apply(normalizar_texto)
    intenciones = dataset["intencion"]

    X_train, X_test, y_train, y_test = train_test_split(
        textos,
        intenciones,
        test_size=0.20,
        random_state=42,
        stratify=intenciones
    )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2),min_df=1,max_df=0.9,sublinear_tf=True)

    X_train_vectorizado = vectorizer.fit_transform(X_train)
    X_test_vectorizado = vectorizer.transform(X_test)

    modelo = MultinomialNB()
    modelo.fit(X_train_vectorizado, y_train)

    y_pred = modelo.predict(X_test_vectorizado)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test,y_pred,average="weighted",zero_division=0)
    recall = recall_score(y_test,y_pred,average="weighted",zero_division=0)
    f1 = f1_score(y_test,y_pred,average="weighted",zero_division=0)

    print("Accuracy:", accuracy)
    print("Precisión:", precision)
    print("Recall:", recall)
    print("F1-score:", f1)

    print("\nReporte de clasificación:")
    print(classification_report(y_test, y_pred, zero_division=0))


    metricas = ['Accuracy', 'Precision', 'Recall', 'F1-score']
    valores = [accuracy, precision, recall, f1]

    plt.figure()
    plt.bar(metricas, valores)
    plt.title("Métricas del modelo de clasificación")
    plt.ylim(0, 1)
    plt.show()

    joblib.dump(modelo, MODELO_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)

    metricas = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

    with open(METRICAS_PATH, "w", encoding="utf-8") as archivo:
        json.dump(metricas, archivo, indent=4)

    print("\nModelo, vectorizador y métricas guardados correctamente.")


if __name__ == "__main__":
    entrenar_modelo()