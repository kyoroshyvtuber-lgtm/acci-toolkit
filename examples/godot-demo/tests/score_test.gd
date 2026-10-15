extends SceneTree

func _initialize() -> void:
    var score = preload("res://score.gd").new()
    if score.value != 0:
        push_error("Initial score must be zero")
        quit(1)
        return
    score.collect()
    score.collect()
    if score.value != 2:
        push_error("Collection must increment score")
        quit(1)
        return
    for i in range(10001):
        score.collect()
    if score.value != 9999:
        push_error("Score must be bounded")
        quit(1)
        return
    score.reset()
    if score.value != 0:
        push_error("Reset must clear score")
        quit(1)
        return
    print("4 gameplay checks passed")
    quit(0)