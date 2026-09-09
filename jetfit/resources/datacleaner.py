import numpy as np
import pandas as pd

file = 'VegasJetFit/jetfit/resources/grbs/221009A/221009A.csv'
delete = 3
data = pd.read_csv(file)

drop_indices = []
for i in data.index:
    if data.loc[i, 'Filter'] == 'xray':
        if data.loc[i, 'Time']/24/3600 < 0.1:
            chance = np.random.randint(1,delete)
            if chance == delete-1:
                drop_indices.append(i)
        if data.loc[i, 'Time']/24/3600 < 1:
            chance = np.random.randint(1,delete+1)
            if chance == delete:
                drop_indices.append(i)
        else:
            chance = np.random.randint(1,delete+4)
            if chance == delete+1:
                drop_indices.append(i)
data = data.drop(drop_indices)
data = data.reset_index(drop=True)
data.to_csv('VegasJetFit/jetfit/resources/grbs/221009A/221009Aclean.csv', index=False)
print(f"Cleaned data saved to {file}")

