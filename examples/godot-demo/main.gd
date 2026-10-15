extends Node

var score = preload("res://score.gd").new()

func _ready() -> void:
    score.collect()
    print("ACCI game fixture ready: energy=", score.value)