import tensorflow as tf
print('TF module:', tf.__version__)
print('backend has function?', hasattr(tf.keras.backend, 'function'))
print('backend attrs sample:', [a for a in dir(tf.keras.backend) if 'func' in a.lower()][:20])
