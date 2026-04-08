import rust_core

print(rust_core.fuzzy_search("иван", ["Иванов Иван", "Петров Петр"], 5))
print(rust_core.employees_count(["Иванов Иван", "Петров Петр", "Иванов Иван"]))
print(rust_core.positions_stats(["Программист", "Преподаватель", "Программист"]))