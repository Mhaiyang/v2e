"""
 @Time    : 17.05.22 13:32
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : frame2crop.py
 @Function:
 
"""
import os
import cv2
from tqdm import tqdm
from misc import check_mkdir

frame_root = '/home/mhy/data/movingcam/frame_demosaicing_5s'
output_root = '/home/mhy/data/movingcam/crop_davis346_demosaicing'

# DAVIS 346
v_step = 280
h_step = 348
v_number = 7
h_number = 7
height = 260
width = 346

# DAVIS 640
# v_step = 512
# h_step = 816
# v_number = 4
# h_number = 3
# height = 480
# width = 640

frame_dir_list = os.listdir(frame_root)
frame_dir_list = sorted(frame_dir_list)
print(frame_dir_list)

for frame_dir_name in tqdm(frame_dir_list):
    frame_dir = os.path.join(frame_root, frame_dir_name)
    frame_list = os.listdir(frame_dir)
    frame_list = sorted(frame_list)
    for frame_name in tqdm(frame_list):
        frame_path = os.path.join(frame_dir, frame_name)
        frame = cv2.imread(frame_path, -1)
        # print(frame.shape)
        # print(frame.dtype)
        # exit(0)

        i = 0
        for v in range(v_number):
            y = v_step * v
            for h in range(h_number):
                x = h_step * h

                crop = frame[y:y + height, x:x + width]

                output_dir = os.path.join(output_root, frame_dir_name + '%02d' % i)
                check_mkdir(output_dir)
                output_path = os.path.join(output_dir, frame_dir_name + '%02d' % i + frame_name)

                cv2.imwrite(output_path, crop)

                i += 1

print('Succeed!')
