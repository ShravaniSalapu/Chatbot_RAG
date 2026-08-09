from app.db import *

print("\nRegistered Tables:\n")

for table in Base.metadata.tables.keys():
    print(table)