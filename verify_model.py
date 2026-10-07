import os
import sys
path = os.path.join('model','best_model_retinascan_v5.keras')
print('model_path:', path)
if not os.path.exists(path):
    print('EXISTS: False')
    sys.exit(2)
else:
    print('EXISTS: True, size_bytes=', os.path.getsize(path))

try:
    import tensorflow as tf
    model = tf.keras.models.load_model(path)
    print('LOAD: OK')
    try:
        layers = len(model.layers)
        print('LAYERS:', layers)
    except Exception:
        print('LAYERS: unknown')
except Exception as e:
    print('LOAD: ERROR:', type(e).__name__, e)
    sys.exit(3)
