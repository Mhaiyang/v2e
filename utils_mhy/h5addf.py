"""
 @Time    : 22.05.22 16:21
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : h5addf.py
 @Function:
 
"""
import os
import sys
sys.path.append('..')
import h5py
import numpy as np
from tqdm import tqdm
import cv2

root_dir = '/home/mhy/v2e/output/raw_demosaicing_polarization'
list = os.listdir(root_dir)
for name in tqdm(list):
    input_path = os.path.join(root_dir, name, name + '_p.h5')
    output_path = os.path.join(root_dir, name, name + '_pf.h5')
    flow_dir = os.path.join(root_dir, name, name + '_flow', 'inference', 'run.epoch-0-npy')

    input = h5py.File(input_path, 'r')

    output = h5py.File(output_path, 'w')
    output.create_dataset('/events', data=input['/events'], chunks=True)
    output.create_dataset('/frame', data=input['/frame'], chunks=True)
    output.create_dataset('/frame_idx', data=input['/frame_idx'], chunks=True)
    output.create_dataset('/frame_ts', data=input['/frame_ts'], chunks=True)

    output.create_dataset('/intensity', data=input['intensity'], chunks=True)
    output.create_dataset('/aolp', data=input['aolp'], chunks=True)
    output.create_dataset('/dolp', data=input['dolp'], chunks=True)

    flow_list = os.listdir(flow_dir)
    flow_list = sorted(flow_list)

    flows = []
    for flow_name in tqdm(flow_list):
        flow_path = os.path.join(flow_dir, flow_name)
        flow = np.load(flow_path)
        dst_size = (input['intensity'].shape[2], input['intensity'].shape[1])
        # print(dst_size)
        # print(flow.shape)
        flow_0 = cv2.resize(flow[:, :, 0], dst_size, cv2.INTER_LINEAR)
        flow_1 = cv2.resize(flow[:, :, 1], dst_size, cv2.INTER_LINEAR)
        flow_01 = np.stack([flow_0, flow_1], axis=2)
        # print(flow_01.shape)
        flows.append(flow_01)

    flows = np.stack(flows, axis=0)

    output.create_dataset('/flow', data=flows, chunks=True)

    output.attrs['sensor_resolution'] = input.attrs['sensor_resolution']

    output.close()

print('Add Flow Succeed!')
