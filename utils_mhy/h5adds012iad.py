"""
 @Time    : 20.09.22 22:20
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : h5adds012iad.py
 @Function:
 
"""
import os
import h5py
import numpy as np
import math
from tqdm import tqdm

mask_aolp = False

root_dir = '/home/mhy/v2e/output/raw_demosaicing_polarization_5s'
list = os.listdir(root_dir)
# list = ['007118']
for name in tqdm(list):
    h5_path = os.path.join(root_dir, name, name + '.h5')
    h5iad_path = os.path.join(root_dir, name, name + '_s012_iad.h5')

    input = h5py.File(h5_path, 'r')
    raw = input['/frame']

    print('--------- Frame ------------')
    print(raw.shape)
    print(raw.dtype)

    i90 = raw[:, 0::2, 0::2].astype(float)
    i45 = raw[:, 0::2, 1::2].astype(float)
    i135 = raw[:, 1::2, 0::2].astype(float)
    i0 = raw[:, 1::2, 1::2].astype(float)

    s0 = i0 + i90
    s1 = i0 - i90
    s2 = i45 - i135

    intensity = (s0 / 2).astype(np.uint8)

    print('--------- Intensity ------------')
    print(intensity.shape)
    print(intensity.dtype)

    aolp = 0.5 * np.arctan2(s2, s1)
    aolp = aolp + 0.5 * math.pi
    aolp = (aolp * (255 / math.pi)).astype(np.uint8)

    print('--------- AoLP ------------')
    print(aolp.shape)
    print(aolp.dtype)

    dolp = np.divide(np.sqrt(np.square(s1) + np.square(s2)), s0, out=np.zeros_like(s0).astype(float), where=s0 != 0)
    dolp = dolp.clip(0.0, 1.0)
    dolp = (dolp * 255).astype(np.uint8)

    print('--------- DoLP ------------')
    print(dolp.shape)
    print(dolp.dtype)

    if mask_aolp:
        mask = np.where(dolp[:, :, :] >= 12.75, 255, 0).astype(np.uint8)
        aolp_masked = np.where(mask[:, :, :] == 255, aolp, 0).astype(np.uint8)

        print('--------- Mask ------------')
        print(mask.shape)
        print(mask.dtype)

        print('--------- AoLP Masked ------------')
        print(aolp_masked.shape)
        print(aolp_masked.dtype)

    s0_save = (s0 / 2).astype(np.uint8)
    s1_save = ((s1 + 255) / 2).astype(np.uint8)
    s2_save = ((s2 + 255) / 2).astype(np.uint8)

    output = h5py.File(h5iad_path, 'w')
    output.create_dataset('/events', data=input['/events'], chunks=True)
    output.create_dataset('/frame', data=input['/frame'], chunks=True)
    output.create_dataset('/frame_idx', data=input['/frame_idx'], chunks=True)
    output.create_dataset('/frame_ts', data=input['/frame_ts'], chunks=True)

    output.create_dataset('/intensity', data=intensity, chunks=True)
    if not mask_aolp:
        output.create_dataset('/aolp', data=aolp, chunks=True)
    else:
        output.create_dataset('/aolp', data=aolp_masked, chunks=True)
    output.create_dataset('/dolp', data=dolp, chunks=True)

    output.create_dataset('/s0', data=s0_save, chunks=True)
    output.create_dataset('/s1', data=s1_save, chunks=True)
    output.create_dataset('/s2', data=s2_save, chunks=True)

    output.attrs['sensor_resolution'] = (raw.shape[2], raw.shape[1])

    output.close()
    print(h5_path + ' Conversion Succeed!')

print('Done!')
