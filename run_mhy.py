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

input_root = '/home/mhy/data/movingcam/crop_davis346_demosaicing'
output_root = '/home/mhy/v2e/output/raw_demosaicing_polarization_new'
# output_root = '/home/mhy/v2e/output/raw_uniform'
check_mkdir(output_root)

list = [
    '000018',
    '000118',
    '001018',
    '001118',
    '002018',
    '002118',
    '003018',
    '003118',
    '004018',
    '004118',
    '005018',
    '005118',
    '007018',
    '007118',
    '008018',
    '008118',
    '009018',
    '009118',
    '010018',
    '010118',
    '013018',
    '013118',
    '014018',
    '014118',
]

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
    threshold = torch.normal(0.3, 0.03, size=[1], dtype=torch.float32)[0]
    sigma = threshold * 0.1
    call_with_args = 'python v2e.py -i {} --polarization_input --input_frame_rate 25 --davis_output --dvs_h5 {}.h5 --dvs_aedat2 {}.aedat --dvs_text {}.txt --overwrite --timestamp_resolution=.0001 --auto_timestamp_resolution=False --dvs_exposure duration 0.001 --output_folder={} --pos_thres={} --neg_thres={} --sigma_thres={} --output_width=346 --output_height=260 --cutoff_hz=30 --refractory_period 0.00004'.format(input_dir, name, name, name, output_dir, threshold, threshold, sigma)

    print(call_with_args)

    os.system(call_with_args)

print('Succeed!')
