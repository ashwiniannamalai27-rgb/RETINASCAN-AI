import importlib
pkgs = [('flask','flask'), ('tensorflow','tensorflow'), ('numpy','numpy'), ('PIL','PIL'), ('cv2','cv2'), ('matplotlib','matplotlib'), ('sklearn','sklearn'), ('gtts','gtts')]
for name, module in pkgs:
    try:
        importlib.import_module(module)
        print(f"{name}: ok")
    except Exception as e:
        print(f"{name}: ERROR: {type(e).__name__}: {e}")
