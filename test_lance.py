import lancedb


uri = "ex_lancedb"
db = lancedb.connect(uri)

data = [
    {"id": "1", "text": "knight", "vector": [0.9, 0.4, 0.8]},
    {"id": "2", "text": "ranger", "vector": [0.8, 0.4, 0.7]},
    {"id": "9", "text": "priest", "vector": [0.6, 0.2, 0.6]},
    {"id": "4", "text": "rogue", "vector": [0.7, 0.4, 0.7]},
]
table = db.create_table("adventurers", data=data, mode="overwrite")