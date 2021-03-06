from scipy.misc import imread, imresize
import os
import numpy as np
import random
import tensorflow as tf
from tensorflow.python.framework import ops
from tensorflow.python.ops import gen_nn_ops
import glob

from fc import FC
from utils import print_prob, visualize, visualize_yang

image_dict = {'tabby': 281, 'laska': 356, 'mastiff': 243}


@ops.RegisterGradient("GuidedRelu")
def _GuidedReluGrad(op, grad):
    return tf.where(0. < grad, gen_nn_ops._relu_grad(grad, op.outputs[0]), tf.zeros(tf.shape(grad)))


@ops.RegisterGradient("NGuidedRelu")
def _GuidedReluGrad(op, grad):
    return tf.where(0. > grad, gen_nn_ops._relu_grad(grad, op.outputs[0]), tf.zeros(tf.shape(grad)))

def super_saliency(tensor, inputs, num_to_viz):
    result = []
    shape = int(np.prod(tensor.get_shape()[1:]))
    tensor_flat = tf.reshape(tensor, [-1, shape])
    pick_indices = np.random.choice(shape, num_to_viz)
    for idx in pick_indices:
        result.append(tf.gradients(tensor_flat[:, idx], inputs)[0])
    return tf.stack(result)

def main():

    sal_map_type = "GuidedBackprop_maxlogit"
    # sal_map_type = "PlainSaliency_maxlogit"
    data_dir = "../VGGImagenet/data_imagenet"
    save_dir = "results/10222017/fc"

    # TODO: extend this part to a list

    image_name = 'tabby'

    n_labels = 5

    n_input = 64

    layers = [
              'conv1_1',
              'conv1_2',
              'pool1',
              'conv2_1',
              'conv2_2',
              'pool2',
              'conv3_1',
              'conv3_2',
              'conv3_3',
              'pool3',
              'conv4_1',
              'conv4_2',
              'conv4_3',
              'pool4',
              'conv5_1',
              'conv5_2',
              'conv5_3',
              'pool5',
              'fc1',
              'fc2',
              'fc3']

    fns = []
    image_list = []
    label_list = []

    # load in the original image and its adversarial examples
    for image_path in glob.glob(os.path.join(data_dir, '{}.png'.format(image_name))):
        fns.append(os.path.basename(image_path).split('.')[0])
        image = imread(image_path, mode='RGB')
        image = imresize(image, (n_input, n_input)).astype(np.float32)
        image_list.append(image)
        onehot_label = np.array([1 if i == image_dict[image_name] else 0 for i in range(n_labels)])
        label_list.append(onehot_label)

    batch_img = np.array(image_list)
    batch_label = np.array(label_list)

    batch_size = batch_img.shape[0]

    # tf session
    sess = tf.Session()

    # construct the graph based on the gradient type we want
    # plain relu vs guidedrelu
    if sal_map_type.split('_')[0] == 'GuidedBackprop':
        eval_graph = tf.get_default_graph()
        with eval_graph.gradient_override_map({'Relu': 'GuidedRelu'}):
                conv_model = FC(sess)

    elif sal_map_type.split('_')[0] == 'NGuidedBackprop':
        eval_graph = tf.get_default_graph()
        with eval_graph.gradient_override_map({'Relu': 'NGuidedRelu'}):
                # load the vgg graph
                # plain_init = true -> load the graph with random weights
                # plain_init = false -> load the graph with pre-trained weights
                conv_model = FC(sess)

    elif sal_map_type.split('_')[0] == 'PlainSaliency':
        # load the vgg graph
        # plain_init = true -> load the graph with random weights
        # plain_init = false -> load the graph with pre-trained weights
        conv_model = FC(sess)

    else:
        raise Exception("Unknown saliency_map type - 1")

    # --------------------------------------------------------------------------
    # Visualize grad-camp and its adversarial examples
    # --------------------------------------------------------------------------
    # Get last convolutional layer gradient for generating gradCAM visualization
    target_conv_layer = conv_model.convnet_out
    if sal_map_type.split('_')[1] == "cost":
        conv_grad = tf.gradients(conv_model.cost, target_conv_layer)[0]
    elif sal_map_type.split('_')[1] == 'maxlogit':
        conv_grad = tf.gradients(conv_model.maxlogit, target_conv_layer)[0]
    elif sal_map_type.split('_')[1] == 'randlogit':
        conv_grad = tf.gradients(conv_model.logits[0], target_conv_layer)[0]
        # conv_grad = tf.gradients(conv_model.logits[random.randint(0, 999)], target_conv_layer)[0]
    else:
        raise Exception("Unknown saliency_map type - 2")

    # normalization
    conv_grad_norm = tf.div(conv_grad, tf.norm(conv_grad) + tf.constant(1e-5))

    # saliency gradient to input layer
    if sal_map_type.split('_')[1] == "cost":
        sal_map = tf.gradients(conv_model.cost, conv_model.imgs)[0]
    elif sal_map_type.split('_')[1] == 'maxlogit':
        sal_map = tf.gradients(conv_model.maxlogit, conv_model.imgs)[0]
    elif sal_map_type.split('_')[1] == 'randlogit':
        sal_map = tf.gradients(conv_model.logits[0], conv_model.imgs)[0]
        # sal_map = tf.gradients(conv_model.logits[random.randint(0, 999)], conv_model.imgs)[0]
    else:
        raise Exception("Unknown saliency_map type - 2")

    # predict
    probs = sess.run(conv_model.probs, feed_dict={conv_model.images: batch_img})

    # sal_map and conv_grad
    sal_map_val, target_conv_layer_val, conv_grad_norm_val =\
        sess.run([sal_map, target_conv_layer, conv_grad_norm],
                 feed_dict={conv_model.images: batch_img, conv_model.labels: batch_label})

    for idx in range(batch_size):
        print_prob(probs[idx])
        visualize(batch_img[idx], target_conv_layer_val[idx], conv_grad_norm_val[idx], sal_map_val[idx],
                  sal_map_type, save_dir, fns[idx], probs[idx])

    # ---------------------------------------------------------------------
    # Layer-by-layer visualizations
    # ---------------------------------------------------------------------
    # num_to_viz = 20
    # for layer_name in layers:
    #
    #     saliencies = super_saliency(vgg.layers_dic[layer_name], vgg.imgs, num_to_viz)
    #     # shape = (num_to_viz, num_input_images, 224, 224, 3)
    #     saliencies_val = sess.run(saliencies, feed_dict={vgg.images: batch_img, vgg.labels: batch_label})
    #     # shape = (num_input_images, num_to_viz, 224, 224, 3)
    #     saliencies_val_trans = np.transpose(saliencies_val, (1, 0, 2, 3, 4))
    #
    #     for idx in range(batch_size):
    #         visualize_yang(batch_img[idx], num_to_viz, saliencies_val_trans[idx], layer_name,
    #                        sal_map_type.split('_')[0], save_dir, fns[idx])




if __name__ == '__main__':
    # setup the GPUs to use
    os.environ['CUDA_VISIBLE_DEVICES'] = '1'
    main()
