### update from original v2e
- `git remote add ups https://github.com/SensorsINI/v2e.git` (perform only once)
- `git fetch ups`
- `git merge ups/master`

## set environment
`workon v2e`

### run v2e with variable parameters
`python run_mhy.py`

### data generation
- `cd utils_mhy`
  - `python demosaicing.py` /home/mhy/data/movingcam/raw ---> /home/mhy/data/movingcam/raw_demosaicing
  - `python raw2frame.py` /home/mhy/data/movingcam/raw_demosaicing ---> /home/mhy/data/movingcam/frame_demosaicing
  - `python frame2crop.py` /home/mhy/data/movingcam/frame_demosaicing ---> /home/mhy/data/movingcam/crop_davis640_demosaicing
- `cd ..`
  - `python run_mhy.py` /home/mhy/data/movingcam/crop_davis640_demosaicing ---> /home/mhy/v2e/output/raw_demosaicing_polarization
- `cd utils_mhy`
  - `python h5addp.py` /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx.h5 ---> /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx_p.h5
  - `python save_intensity.py` /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx_p.h5 --- > /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx_intensity
  - or `python save_direction.py`
- `cd ../../flownet2`
- `conda activate flownet2`
  - `python my_inference.py` /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx_intensity ---> /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx_flow/inference/run.epoch-0-flow-vis
- `cd ../../v2e/utils_mhy`
- `workon v2e`
  - `python h5addf.py` /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx_p.h5 ---> /home/mhy/v2e/output/raw_demosaicing_polarization/xxxxx/xxxxx_pf.h5
  - or `python h5addrawf`
  - `python check_h5pf.py`
  - 