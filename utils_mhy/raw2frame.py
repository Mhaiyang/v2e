"""
 @Time    : 17.05.22 13:19
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : raw2frame.py
 @Function:
 
"""
import os
import sys

sys.path.append('..')
import cv2
import numpy as np
from tqdm import tqdm
from misc import check_mkdir

raw_dir = '/home/mhy/data/movingcam/raw_demosaicing'
output_dir = '/home/mhy/data/movingcam/frame_demosaicing'
check_mkdir(output_dir)

raw_list = os.listdir(raw_dir)
raw_list = sorted(raw_list)
print(raw_list)

for raw_name in tqdm(raw_list):
    raw_path = os.path.join(raw_dir, raw_name)
    raw = np.load(raw_path)
    frame_dir = os.path.join(output_dir, raw_name.split('.')[0])
    check_mkdir(frame_dir)

    number = raw.shape[0]
    for index in tqdm(range(number)):
        frame_raw = raw[index, :, :]
        # print(frame_raw.shape)
        # print(frame_raw.dtype)
        # exit(0)
        frame_path = os.path.join(frame_dir, '%04d.png' % index)
        cv2.imwrite(frame_path, frame_raw)

print('Succeed!')

