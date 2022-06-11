"""
 @Time    : 22.05.22 17:06
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : check_h5pf.py
 @Function:
 
"""
import os
import h5py
from tqdm import tqdm

root_dir = '/home/mhy/v2e/output/raw_demosaicing_polarization'
list = os.listdir(root_dir)
for name in tqdm(list):
    print(name)

    path = os.path.join(root_dir, name, name + '_pff.h5')

    f = h5py.File(path, 'r')
    for key in f.keys():
        print(f[key].name)
        print(f[key].shape)
        print(f[key].dtype)
    for item in f.attrs.items():
        print(item)

    print(f['/frame_idx'][:])
    print(f['/frame_ts'][:])

    # exit(0)

print('Done!')

