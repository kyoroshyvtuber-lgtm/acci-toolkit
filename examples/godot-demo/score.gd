extends RefCounted

var value: int = 0

func collect() -> void:
    value = mini(value + 1, 9999)

func reset() -> void:
    value = 0