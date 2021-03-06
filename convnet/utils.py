import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt, gridspec

from imagenet_classes import class_names
from skimage.transform import resize

n_input = 64

# returns the top1 string
def print_prob(prob):
    pred = (np.argsort(prob)[::-1])
    # Gegt top1 label
    top1 = [(pred[0], class_names[pred[0]], prob[pred[0]])] # pick the most likely class
    print("Top1: ", top1)

    # Get top5 label
    top5 = [(pred[i], class_names[pred[i]], prob[pred[i]]) for i in range(5)]
    print("Top5: ", top5)


def grad_cam(conv_output, conv_grad):
    output = conv_output  # [7,7,512]
    grads_val = conv_grad  # [7,7,512]

    weights = np.mean(grads_val, axis=(0, 1))  # [512]
    cam = np.ones(output.shape[0: 2], dtype=np.float32)  # [7,7]

    # Taking a weighted average
    for i, w in enumerate(weights):
        cam += w * output[:, :, i]

    # Passing through ReLU
    cam = np.maximum(cam, 0)
    cam = cam / np.max(cam)  # scale 0 to 1.0
    cam = resize(cam, (n_input, n_input))
    return cam

def sal_pool_normalization(sal_pool):
        sal_pool -= np.min(sal_pool)
        sal_pool /= sal_pool.max()
        print(sal_pool.shape)

def visualize(image, conv_output, conv_grad, sal_map, sal_map_type, save_dir, fn, prob):

    cam = grad_cam(conv_output, conv_grad)

    # normalizations
    sal_map -= np.min(sal_map)
    sal_map /= sal_map.max()

    img = image.astype(float)
    img -= np.min(img)
    img /= img.max()
    # print(img)

    guided_grad_cam = np.dstack((
        sal_map[:, :, 0] * cam,
        sal_map[:, :, 1] * cam,
        sal_map[:, :, 2] * cam,
    ))

    fig = plt.figure()

    gs = gridspec.GridSpec(1, 4, wspace=0.2, hspace=0.2)

    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(img)
    ax.set_title('Input Image', fontsize=8)
    ax.tick_params(axis='both', which='major',  labelsize=6)

    ax = fig.add_subplot(gs[0, 1])
    ax.imshow(cam)
    ax.set_title('Grad-Cam', fontsize=8)
    ax.tick_params(axis='both', which='major',  labelsize=6)

    pred = (np.argsort(prob)[::-1])
    ax.set_xlabel('input: {}, pred_class: {} ({:.2f})'.
                  format(fn, class_names[pred[0]], prob[pred[0]]), fontsize=8)

    ax = fig.add_subplot(gs[0, 2])
    ax.imshow(sal_map)
    ax.set_title(sal_map_type, fontsize=8)
    ax.tick_params(axis='both', which='major',  labelsize=6)

    ax = fig.add_subplot(gs[0, 3])
    ax.imshow(guided_grad_cam)
    ax.set_title('guided Grad-Gam', fontsize=8)
    ax.tick_params(axis='both', which='major',  labelsize=6)

    # saved results path
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    print('Saving {}_cam_{}.png'.format(sal_map_type, fn))
    plt.savefig(os.path.join(save_dir, "{}_cam_{}.png".format(sal_map_type, fn)))

    # plot guided backpropagation separately
    fig2 = plt.figure()
    ax2 = fig2.add_subplot(111)
    ax2.imshow(sal_map)
    ax2.axis('off')
    print('Saving {}_{}.png'.format(sal_map_type, fn))
    plt.savefig(os.path.join(save_dir, "{}_{}.png".format(sal_map_type, fn)))

    # plot input separately
    fig3 = plt.figure()
    ax3 = fig3.add_subplot(111)
    ax3.imshow(img)
    ax3.axis('off')
    plt.savefig(os.path.join(save_dir, "{}.png".format(fn)))

def visualize_yang(batch_img, num_neurons, neuron_saliencies, layer_name, sal_type, save_dir, fn):

    for idx in range(num_neurons):

        dir = save_dir + '/{}'.format(layer_name)

        sal_map = neuron_saliencies[idx]
        sal_map -= np.min(sal_map)
        sal_map /= sal_map.max()

        plt.imshow(sal_map)

        if not os.path.exists(dir):
            os.makedirs(dir)
        plt.savefig(os.path.join(dir,
                                 "layer_name={}_idx={}_sal_type={}_image_info={}.png"
                                 .format(layer_name, idx, sal_type, fn)))
        plt.close()


