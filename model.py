from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

def conv_relu(input, kernel_shape, bias_shape):
    # Create variable named "weights".
    with tf.variable_scope("conv_weights"):
        weights = tf.get_variable("weights", kernel_shape,
            initializer=tf.random_normal_initializer())
        variable_summaries(weights)
    # Create variable named "biases".
    with tf.variable_scope("conv_biases"):
        biases = tf.get_variable("biases", bias_shape,
            initializer=tf.constant_initializer(0.1))
        variable_summaries(biases)
    conv = tf.nn.conv2d(input, weights,
        strides=[1, 1, 1, 1], padding='VALID')
    return tf.nn.relu(conv + biases)

def variable_summaries(var):
    """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
    with tf.name_scope('summaries'):
        mean = tf.reduce_mean(var)
        tf.summary.scalar('mean', mean)
        with tf.name_scope('stddev'):
            stddev = tf.sqrt(tf.reduce_mean(tf.square(var - mean)))
        tf.summary.scalar('stddev', stddev)
        tf.summary.scalar('max', tf.reduce_max(var))
        tf.summary.scalar('min', tf.reduce_min(var))
        tf.summary.histogram('histogram', var)

class Model:
    def __init__(self, max_sent_len, num_labels, vocab_size, embedding_dim,
                 learning_rate):
        in_channels = 1
        out_channels = 100

        with tf.name_scope('placeholders'):
            self.keep_prob = tf.placeholder('float32', shape=(), name='drop')
            self.sentence = tf.placeholder(tf.int32, shape=(None, max_sent_len))
            self.target = tf.placeholder(tf.float32, shape=(None, num_labels))

        with tf.variable_scope('embedding'):
            embedding = tf.Variable(tf.constant(0.0, shape=[vocab_size, embedding_dim]), trainable=True)
            self.embedding_placeholder = tf.placeholder(tf.float32, [vocab_size, embedding_dim])
            self.embedding_init = embedding.assign(self.embedding_placeholder)

            sent_emb = tf.nn.embedding_lookup(embedding, self.sentence)

        with tf.variable_scope('networks'):
            sent_emb = tf.expand_dims(sent_emb, -1)

            with tf.variable_scope('trigram'):
                features = conv_relu(sent_emb, [3, embedding_dim, in_channels, out_channels], [out_channels])
                features = tf.squeeze(features, 2)
                trigram_features = tf.reduce_max(features, axis=1) # Max-pooling

            with tf.variable_scope('fourgram'):
                features = conv_relu(sent_emb, [4, embedding_dim, in_channels, out_channels], [out_channels])
                features = tf.squeeze(features, 2)
                fourgram_features = tf.reduce_max(features, axis=1) # Max-pooling

            with tf.variable_scope('fivegram'):
                features = conv_relu(sent_emb, [5, embedding_dim, in_channels, out_channels], [out_channels])
                features = tf.squeeze(features, 2)
                fivegram_features = tf.reduce_max(features, axis=1) # Max-pooling

            features = tf.concat([trigram_features, fourgram_features, fivegram_features], axis=1)
            features_drop = tf.nn.dropout(features, self.keep_prob)

        with tf.variable_scope("predictions"):
            with tf.variable_scope('final_weight'):
                final_w = tf.Variable(tf.random_normal([3 * out_channels, num_labels]), name='final_w')
                variable_summaries(final_w)
            with tf.variable_scope('final_bias'):
                final_b = tf.Variable(tf.random_normal([num_labels]), name='final_bias')
                variable_summaries(final_b)
            self.scores = tf.nn.xw_plus_b(features_drop, final_w, final_b)
            self.prediction = tf.argmax(self.scores, 1)

        with tf.name_scope("loss"):
            losses = tf.nn.softmax_cross_entropy_with_logits(labels = self.target, logits = self.scores)
            self.loss = tf.reduce_mean(losses)

        with tf.name_scope("accuracy"):
            correct_preds = tf.equal(tf.argmax(self.target, 1), self.prediction)
            self.accuracy = tf.reduce_mean(tf.cast(correct_preds, tf.float32))
            self.correct = tf.reduce_sum(tf.cast(correct_preds, tf.float32))

        with tf.name_scope("optimization"):
            optimizer = tf.train.AdamOptimizer(learning_rate)
            gvs = optimizer.compute_gradients(self.loss)
            self.optimize = optimizer.apply_gradients(gvs)

        # Operation for initializing the variables
        self.init = tf.global_variables_initializer()

        # Operation to save and restore all the variables.
        self.saver = tf.train.Saver()

        # merge all summaries into a single "operation" which we can execute in a session
        self.summary_op = tf.summary.merge_all()

    def train(self, sess, batch, keep_prob = 0.5):
        batch_sentences, batch_targets = batch
        _, batch_loss, batch_accuracy = sess.run(
                        [self.optimize, self.loss, self.accuracy],
                        feed_dict = {
                            self.keep_prob: keep_prob,
                            self.sentence: batch_sentences,
                            self.target: batch_targets,
                        })
        return batch_loss, batch_accuracy

    def evaluate(self, sess, batch):
        batch_sentences, batch_targets = batch
        batch_correct = sess.run(
                        self.correct,
                        feed_dict = {
                            self.keep_prob: 1,
                            self.sentence: batch_sentences,
                            self.target: batch_targets,
                        })
        return batch_correct
