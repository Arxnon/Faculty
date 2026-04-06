import rust_core

data = ["Иванов Иван",
        "Петров Петр",
        "Содоров Сидор"]

result = rust_core.fuzzy_search("иван", data, 5)
print(result)