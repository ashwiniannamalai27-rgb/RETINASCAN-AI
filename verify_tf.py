import tensorflow as tf
print('TF_VERSION:', tf.__version__)
print('EAGER:', tf.executing_eagerly())
print('ADD:', (tf.constant([1.0,2.0,3.0]) + 1.0).numpy())
