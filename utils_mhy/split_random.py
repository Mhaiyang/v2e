"""
 @Time    : 30.09.22 10:36
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : split_random.py
 @Function:
 
"""
import os
import random

root = '/home/mhy/v2e/output/raw_demosaicing_polarization_5s'
list = [root + '/' + x + '/' + x + '_s012_iad.h5' for x in os.listdir(root)]

random.shuffle(list)

ratio = 0.7

number = int(len(list) * 0.7)

# train txt
train_txt_path = '/home/mhy/firenet-pdavis/data/movingcam/train_s012_iad.txt'
with open(train_txt_path, 'w') as fp:
    for item in list[:number]:
        fp.write("%s\n" % item)
    print('Train txt done.')

# test txt
test_txt_path = '/home/mhy/firenet-pdavis/data/movingcam/test_s012_iad.txt'
with open(test_txt_path, 'w') as fp:
    for item in list[number:]:
        fp.write("%s\n" % item)
    print('Test txt done.')
