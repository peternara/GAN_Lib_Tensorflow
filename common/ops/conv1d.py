"""

"""

import numpy as np
import tensorflow as tf

_default_weightnorm = False


def enable_default_weightnorm():
    global _default_weightnorm
    _default_weightnorm = True


def Conv1D(name, input_dim, output_dim, filter_size, inputs, he_init=True, mask_type=None, stride=1, weightnorm=None,
           biases=True, gain=1.):
    """
    Args:
      name:
      input_dim:
      output_dim:
      filter_size:
      inputs: tensor of shape (batch size, num_channels, width)
      he_init:
      mask_type: one of None, 'a', 'b'
      stride:
      weightnorm:
      biases:
      gain:

    Returns:
      tensor of shape (batch size, num channels, width)
    """
    with tf.variable_scope(name):
        if mask_type is not None:
            mask_type, mask_n_channels = mask_type

            mask = np.ones(
                (filter_size, input_dim, output_dim),
                dtype='float32'
            )
            center = filter_size // 2

            # Mask out future locations
            # filter shape is (width, input channels, output channels)
            mask[center + 1:, :, :] = 0.

            # Mask out future channels
            for i in range(mask_n_channels):
                for j in range(mask_n_channels):
                    if (mask_type == 'a' and i >= j) or (mask_type == 'b' and i > j):
                        mask[center, i::mask_n_channels, j::mask_n_channels] = 0.

        def uniform(stdev, size):
            return np.random.uniform(
                low=-stdev * np.sqrt(3),
                high=stdev * np.sqrt(3),
                size=size
            ).astype('float32')

        fan_in = input_dim * filter_size
        fan_out = output_dim * filter_size / stride

        if mask_type is not None:  # only approximately correct
            fan_in /= 2.
            fan_out /= 2.

        if he_init:
            filters_stdev = np.sqrt(4. / (fan_in + fan_out))
        else:  # Normalized init (Glorot & Bengio)
            filters_stdev = np.sqrt(2. / (fan_in + fan_out))

        filter_values = uniform(
            filters_stdev,
            (filter_size, input_dim, output_dim)
        )
        # print "WARNING IGNORING GAIN"
        filter_values *= gain

        filters = tf.get_variable(name='Filters',
                                  dtype=tf.float32,
                                  initializer=filter_values)  # tf.glorot_uniform_initializer()

        if weightnorm is None:
            weightnorm = _default_weightnorm
        if weightnorm:
            norm_values = np.sqrt(np.sum(np.square(filter_values), axis=(0, 1)))
            target_norms = tf.get_variable(name='g',
                                           dtype=tf.float32,
                                           initializer=norm_values)
            with tf.name_scope('weightnorm'):
                norms = tf.sqrt(tf.reduce_sum(tf.square(filters), reduction_indices=[0, 1]))
                filters = filters * (target_norms / norms)

        if mask_type is not None:
            with tf.name_scope('filter_mask'):
                filters = filters * mask

        result = tf.nn.conv1d(
            value=inputs,
            filters=filters,
            stride=stride,
            padding='SAME',
            data_format='NHWC'
        )

        if biases:
            _biases = tf.get_variable(name='Biases', shape=[output_dim, ], dtype=tf.float32,
                                      initializer=tf.constant_initializer(0.))

            result = tf.expand_dims(result, 3)
            result = tf.nn.bias_add(result, _biases, data_format='NHWC')
            result = tf.squeeze(result)

        return result
