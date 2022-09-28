"""
 @Time    : 17.05.22 10:57
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : run_mhy.py
 @Function:
 
"""
import os
import torch
import sys
sys.path.append('..')
from misc import check_mkdir

input_root = '~/data/movingcam/crop_davis640_demosaicing_5s'
output_root = '~/v2e/output/raw_demosaicing_polarization_5s'
check_mkdir(output_root)

# list = [
#     '001004',
#     '001104',
#     '004004',
#     '004104',
#     '005004',
#     '005104',
#     '007004',
#     '007104',
#     '008004',
#     '008104',
#     '009004',
#     '009104',
#     '010004',
#     '010104',
#     '013004',
#     '013104',
#     '014004',
#     '014104',
#     '015001',
#     '015101',
# ]

list = os.listdir(input_root)
list = sorted(list)

for name in list:
    input_dir = os.path.join(input_root, name)
    output_dir = os.path.join(output_root, name)

    # call_with_args = 'python v2e.py -i {} --polarization_input --input_frame_rate 25 --davis_output --dvs_h5 {}.h5 --dvs_aedat2 {}.aedat --dvs_text {}.txt --overwrite --timestamp_resolution=.005 --auto_timestamp_resolution=False --dvs_exposure duration 0.005 --output_folder={} --pos_thres=.05 --neg_thres=.05 --sigma_thres=0.01 --output_width=346 --output_height=260 --cutoff_hz=5 --refractory_period 0.0001'.format(input_dir, name, name, name, output_dir)

    # call_with_args = 'python v2e.py -i {} --polarization_input --input_frame_rate 25 --davis_output --dvs_h5 {}.h5 --dvs_aedat2 {}.aedat --dvs_text {}.txt --overwrite --timestamp_resolution=.005 --auto_timestamp_resolution=False --dvs_exposure duration 0.005 --output_folder={} --pos_thres=.1 --neg_thres=.1 --sigma_thres=0.03 --output_width=346 --output_height=260 --cutoff_hz=9 --refractory_period 0.0002'.format(
    #     input_dir, name, name, name, output_dir)

    # too slow
    # call_with_args = 'python v2e.py -i {} --polarization_input --input_frame_rate 25 --davis_output --dvs_h5 {}.h5 --dvs_aedat2 {}.aedat --dvs_text {}.txt --overwrite --timestamp_resolution=.00005 --auto_timestamp_resolution=False --dvs_exposure duration 0.005 --output_folder={} --pos_thres=.1 --neg_thres=.1 --sigma_thres=0.02 --output_width=346 --output_height=260 --cutoff_hz=30 --refractory_period 0.00002'.format(
    #     input_dir, name, name, name, output_dir)

    # gaussian-sampled threshold
    threshold = torch.normal(0.12, 0.02, size=[1], dtype=torch.float32)[0]
    sigma = threshold * 0.1
    call_with_args = 'CUDA_VISIBLE_DEVICES=0 python v2e.py -i {} --polarization_input --input_frame_rate 25 --davis_output --dvs_h5 {}.h5 --dvs_aedat2 {}.aedat --dvs_text {}.txt --overwrite --timestamp_resolution=.0001 --auto_timestamp_resolution=False --dvs_exposure duration 0.005 --output_folder={} --pos_thres={} --neg_thres={} --sigma_thres={} --output_width=640 --output_height=480 --cutoff_hz=30 --refractory_period 0.00003 --batch_size 16'.format(input_dir, name, name, name, output_dir, threshold, threshold, sigma)

    print(call_with_args)

    os.system(call_with_args)

print('Succeed!')
