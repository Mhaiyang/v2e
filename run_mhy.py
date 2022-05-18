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
output_root = '/home/mhy/v2e/output/raw_demosaicing'
# output_root = '/home/mhy/v2e/output/raw_uniform'
check_mkdir(output_root)

list = [
    # '00006',
    # '00104',
    # '00303',
    # '00404',
    # '00503',
    '00704',
    # '00805',
    # '01304',
    # '01404',
    # '01505'
]

for name in list:
    input_dir = os.path.join(input_root, name)
    output_dir = os.path.join(output_root, name)

    call_with_args = 'python v2e.py -i {} --input_frame_rate 25 --davis_output --dvs_h5 {}.h5 --dvs_aedat2 {}.aedat --dvs_text {}.txt --overwrite --timestamp_resolution=.005 --auto_timestamp_resolution=False --dvs_exposure duration 0.005 --output_folder={} --pos_thres=.08 --neg_thres=.08 --sigma_thres=0.02 --output_width=640 --output_height=480 --cutoff_hz=9 --start_time=1 --stop_time=3 --refractory_period 0.0002'.format(input_dir, name, name, name, output_dir)

    print(call_with_args)

    os.system(call_with_args)

print('Succeed!')
