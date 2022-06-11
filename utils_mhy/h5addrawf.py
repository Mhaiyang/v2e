"""
 @Time    : 11.06.22 16:07
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : h5addrawf.py
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
    input_path = os.path.join(root_dir, name, name + '_pf.h5')
    output_path = os.path.join(root_dir, name, name + '_pff.h5')
    i90_flow_dir = os.path.join(root_dir, name, name + '_frame_flow', 'i90', 'inference', 'run.epoch-0-npy')
    i45_flow_dir = os.path.join(root_dir, name, name + '_frame_flow', 'i45', 'inference', 'run.epoch-0-npy')
    i135_flow_dir = os.path.join(root_dir, name, name + '_frame_flow', 'i135', 'inference', 'run.epoch-0-npy')
    i0_flow_dir = os.path.join(root_dir, name, name + '_frame_flow', 'i0', 'inference', 'run.epoch-0-npy')

    input = h5py.File(input_path, 'r')

    output = h5py.File(output_path, 'w')
    output.create_dataset('/events', data=input['/events'], chunks=True)
    output.create_dataset('/frame', data=input['/frame'], chunks=True)
    output.create_dataset('/frame_idx', data=input['/frame_idx'], chunks=True)
    output.create_dataset('/frame_ts', data=input['/frame_ts'], chunks=True)

    output.create_dataset('/intensity', data=input['intensity'], chunks=True)
    output.create_dataset('/aolp', data=input['aolp'], chunks=True)
    output.create_dataset('/dolp', data=input['dolp'], chunks=True)

    output.create_dataset('/flow', data=input['flow'], chunks=True)

    i90_flow_list = os.listdir(i90_flow_dir)
    i90_flow_list = sorted(i90_flow_list)

    frame_flows = []
    for flow_name in tqdm(i90_flow_list):
        i90_flow_path = os.path.join(i90_flow_dir, flow_name)
        i45_flow_path = os.path.join(i45_flow_dir, flow_name)
        i135_flow_path = os.path.join(i135_flow_dir, flow_name)
        i0_flow_path = os.path.join(i0_flow_dir, flow_name)

        i90_flow = np.load(i90_flow_path)
        i45_flow = np.load(i45_flow_path)
        i135_flow = np.load(i135_flow_path)
        i0_flow = np.load(i0_flow_path)

        dst_size = (input['intensity'].shape[2], input['intensity'].shape[1])

        frame_flow = np.zeros((input['frame'].shape[1], input['frame'].shape[2], 2)).astype(np.float32)

        i90_flow_resize_0 = cv2.resize(i90_flow[:, :, 0], dst_size, cv2.INTER_AREA)
        i45_flow_resize_0 = cv2.resize(i45_flow[:, :, 0], dst_size, cv2.INTER_AREA)
        i135_flow_resize_0 = cv2.resize(i135_flow[:, :, 0], dst_size, cv2.INTER_AREA)
        i0_flow_resize_0 = cv2.resize(i0_flow[:, :, 0], dst_size, cv2.INTER_AREA)

        i90_flow_resize_1 = cv2.resize(i90_flow[:, :, 1], dst_size, cv2.INTER_AREA)
        i45_flow_resize_1 = cv2.resize(i45_flow[:, :, 1], dst_size, cv2.INTER_AREA)
        i135_flow_resize_1 = cv2.resize(i135_flow[:, :, 1], dst_size, cv2.INTER_AREA)
        i0_flow_resize_1 = cv2.resize(i0_flow[:, :, 1], dst_size, cv2.INTER_AREA)

        frame_flow[0::2, 0::2, 0] = i90_flow_resize_0
        frame_flow[0::2, 1::2, 0] = i45_flow_resize_0
        frame_flow[1::2, 0::2, 0] = i135_flow_resize_0
        frame_flow[1::2, 1::2, 0] = i0_flow_resize_0

        frame_flow[0::2, 0::2, 1] = i90_flow_resize_1
        frame_flow[0::2, 1::2, 1] = i45_flow_resize_1
        frame_flow[1::2, 0::2, 1] = i135_flow_resize_1
        frame_flow[1::2, 1::2, 1] = i0_flow_resize_1

        frame_flows.append(frame_flow)

    frame_flows = np.stack(frame_flows, axis=0)

    output.create_dataset('/frame_flow', data=frame_flows, chunks=True)

    output.attrs['sensor_resolution'] = input.attrs['sensor_resolution']

    output.close()

print('Add Flow Succeed!')
