import pandas as pd
from sklearn.model_selection import train_test_split

ratings = pd.read_csv("ratings.csv")

train_rows = []
test_rows = []

for uid, g in ratings.groupby("userId"):
    if len(g) < 5:
        continue
    train, test = train_test_split(g, test_size=0.2, random_state=42)
    train_rows.append(train)
    test_rows.append(test)

train_df = pd.concat(train_rows)
test_df = pd.concat(test_rows)
