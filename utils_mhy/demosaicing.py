"""
 @Time    : 17.05.22 11:25
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : demosaicing.py
 @Function:
 
"""
import os
from tqdm import tqdm
import numpy as np
import cv2

raw_dir = '/home/mhy/data/movingcam/raw'
raw_demosaicing_dir = '/home/mhy/data/movingcam/raw_demosaicing'
if not os.path.exists(raw_demosaicing_dir):
    os.makedirs(raw_demosaicing_dir)

npy_list = os.listdir(raw_dir)
for name in tqdm(npy_list):
    npy_path = os.path.join(raw_dir, name)
    raw = np.load(npy_path)
    raw_uint8 = (raw / 65535 * 255).astype(np.uint8)

    # split to I90, I45, I0, I135
    I90_bayer = raw_uint8[:, 0::2, 0::2]
    I45_bayer = raw_uint8[:, 0::2, 1::2]
    I135_bayer = raw_uint8[:, 1::2, 0::2]
    I0_bayer = raw_uint8[:, 1::2, 1::2]

    I = np.zeros_like(raw_uint8).astype(np.uint8)

    # demosaicing
    for x in range(raw_uint8.shape[0]):
        i90 = cv2.cvtColor(I90_bayer[x, :, :], cv2.COLOR_BAYER_BG2GRAY)
        i45 = cv2.cvtColor(I45_bayer[x, :, :], cv2.COLOR_BAYER_BG2GRAY)
        i135 = cv2.cvtColor(I135_bayer[x, :, :], cv2.COLOR_BAYER_BG2GRAY)
        i0 = cv2.cvtColor(I0_bayer[x, :, :], cv2.COLOR_BAYER_BG2GRAY)

        I[x, 0::2, 0::2] = i90
        I[x, 0::2, 1::2] = i45
        I[x, 1::2, 0::2] = i135
        I[x, 1::2, 1::2] = i0

    np.save(os.path.join(raw_demosaicing_dir, name), I)

print('Succeed!')
