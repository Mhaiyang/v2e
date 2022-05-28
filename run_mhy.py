"""
 @Time    : 17.05.22 10:57
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : run_mhy.py
 @Function:
 
"""
import os
import sys
sys.path.append('..')
from misc import check_mkdir

input_root = '/home/mhy/data/movingcam/crop_davis640_demosaicing'
output_root = '/home/mhy/v2e/output/raw_demosaicing_polarization'
# output_root = '/home/mhy/v2e/output/raw_uniform'
check_mkdir(output_root)

list = [
    '00402',
    '00403',
    '00405',
    '00502',
    '00503',
    '00505',
    '00803',
    '00804',
    '00805',
    '00903',
    '00904',
    '00905',
    '01001',
    '01002',
    '01005',
    '01303',
    '01304',
    '01305',
    '00702',
    '00704',
    '00705',
    '01402',
    '01404',
    '01405',
]

for name in list:
    input_dir = os.path.join(input_root, name)
    output_dir = os.path.join(output_root, name)

    call_with_args = 'python v2e.py -i {} --polarization_input --input_frame_rate 25 --davis_output --dvs_h5 {}.h5 --dvs_aedat2 {}.aedat --dvs_text {}.txt --overwrite --timestamp_resolution=.005 --auto_timestamp_resolution=False --dvs_exposure duration 0.005 --output_folder={} --pos_thres=.05 --neg_thres=.05 --sigma_thres=0.01 --output_width=640 --output_height=480 --cutoff_hz=9 --start_time=1 --stop_time=9 --refractory_period 0.0002'.format(input_dir, name, name, name, output_dir)

    print(call_with_args)

    os.system(call_with_args)

print('Succeed!')
