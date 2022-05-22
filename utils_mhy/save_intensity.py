"""
 @Time    : 22.05.22 14:12
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : save_intensity.py
 @Function:
 
"""
import os
import sys
sys.path.append('..')
import cv2
import h5py
from tqdm import tqdm
from misc import check_mkdir

root_dir = '/home/mhy/v2e/output/raw_demosaicing_polarization'
list = os.listdir(root_dir)
for name in tqdm(list):
    h5p_path = os.path.join(root_dir, name, name + '_p.h5')
    intensity_dir = os.path.join(root_dir, name, name + '_intensity')
    check_mkdir(intensity_dir)

    input = h5py.File(h5p_path, 'r')

    intensity = input['/intensity']

    print(intensity.shape)
    print(intensity.dtype)

    for i in tqdm(range(intensity.shape[0])):
        intensity_path = os.path.join(intensity_dir, '%05d.png' % i)
        cv2.imwrite(intensity_path, intensity[i, :, :])

print('Done')
