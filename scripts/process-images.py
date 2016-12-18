from glob import glob
import numpy as np
import os
from scipy.signal import convolve2d
from scipy.misc import imread, imsave
from skimage.transform import rescale

scripts_folder = os.path.expanduser('~/projects/snoggle/scripts/')
input_folder = os.path.join(scripts_folder, 'raw-images')
output_folder = os.path.join(scripts_folder, 'processed-images')

MASK = rescale(imread(os.path.join(scripts_folder, 'mask.jpg'), flatten=True) / 255., .1)


def mask_all_images():
    for path in glob('%s/Boggle*.jpg' % input_folder):
        filename = os.path.basename(path)
        letter = filename.split('-')[0].split(' ')[-1]
        print letter,
        im = rescale(imread(os.path.join(input_folder, filename)) / 255., .1)
        masked = mask_image(im)
        imsave(os.path.join(output_folder, '%s.png' % letter), masked)


def mask_image(im):
    gray = grayscale(im)
    bw1 = gray > .01 + gray[1:3, 50:-50].mean()
    bw2 = gray > .01 + gray[80:-80, -5:-1].mean()
    x = find_first_peak(bw1.mean(0))
    y = find_first_peak(bw1.mean(1))
    width = find_last_peak(bw2.mean(0)) - x
    scale = width / float(MASK.shape[1])
    print width, scale
    mask = rescale(MASK, scale)
    masked = np.zeros((mask.shape[0], mask.shape[1], 4))
    masked[:, :, :3] = im[y:mask.shape[0] + y, x:mask.shape[1] + x, ]
    masked[:, :, 3] = 1-mask
    return masked


def find_first_peak(a):
    return np.argmax(a[1:30] - a[0:29])


def find_last_peak(a):
    return np.argmax(a[-30:-1] - a[-29:]) + len(a) - 30


def grayscale(im):
    return im[:, :, :3].mean(axis=2)
