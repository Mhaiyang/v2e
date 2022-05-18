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
  - `python demosaicing.py`
  - `python raw2frame.py`
  - `python frame2crop.py`
- `cd ..`
  - `python run_mhy.py`
  - 
