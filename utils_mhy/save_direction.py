"""
 @Time    : 11.06.22 13:02
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : save_direction.py
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
    h5p_path = os.path.join(root_dir, name, name + '_pf.h5')
    frame_dir = os.path.join(root_dir, name, name + '_frame')
    i90_dir = os.path.join(frame_dir, 'i90')
    i45_dir = os.path.join(frame_dir, 'i45')
    i135_dir = os.path.join(frame_dir, 'i135')
    i0_dir = os.path.join(frame_dir, 'i0')
    check_mkdir(i90_dir)
    check_mkdir(i45_dir)
    check_mkdir(i135_dir)
    check_mkdir(i0_dir)

    input = h5py.File(h5p_path, 'r')

    frame = input['/frame']

    print('before:', frame.shape[1:], frame.dtype)

    size = ((int(frame.shape[2] / 2) // 64) * 64, (int(frame.shape[1] / 2) // 64) * 64)

    for i in tqdm(range(frame.shape[0])):
        i90 = frame[i, 0::2, 0::2]
        i45 = frame[i, 0::2, 1::2]
        i135 = frame[i, 1::2, 0::2]
        i0 = frame[i, 1::2, 1::2]

        i90_save = cv2.resize(i90, size, cv2.INTER_AREA)
        i45_save = cv2.resize(i45, size, cv2.INTER_AREA)
        i135_save = cv2.resize(i135, size, cv2.INTER_AREA)
        i0_save = cv2.resize(i0, size, cv2.INTER_AREA)

        if i == 0:
            print('after i90:', i90_save.shape, i90_save.dtype)
            print('after i45:', i45_save.shape, i45_save.dtype)
            print('after i135:', i135_save.shape, i135_save.dtype)
            print('after i0:', i0_save.shape, i0_save.dtype)

        i90_path = os.path.join(i90_dir, '%05d.png' % i)
        i45_path = os.path.join(i45_dir, '%05d.png' % i)
        i135_path = os.path.join(i135_dir, '%05d.png' % i)
        i0_path = os.path.join(i0_dir, '%05d.png' % i)

        cv2.imwrite(i90_path, i90_save)
        cv2.imwrite(i45_path, i45_save)
        cv2.imwrite(i135_path, i135_save)
        cv2.imwrite(i0_path, i0_save)

print('Done')
