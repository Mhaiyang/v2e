"""
 @Time    : 16.09.22 22:56
 @Author  : Haiyang Mei
 @E-mail  : haiyang.mei@outlook.com
 
 @Project : v2e
 @File    : emulator_mhy.py
 @Function:
 
"""
"""
DVS simulator.
Compute events from input frames.
"""
import atexit
import logging
import math
import os
import random
from typing import Optional

import cv2
import h5py
import numpy as np
import torch  # https://pytorch.org/docs/stable/torch.html
from screeninfo import get_monitors

from v2ecore.emulator_utils import compute_event_map
from v2ecore.emulator_utils import generate_shot_noise
from v2ecore.emulator_utils import lin_log
from v2ecore.emulator_utils import low_pass_filter
from v2ecore.emulator_utils import rescale_intensity_frame
from v2ecore.emulator_utils import subtract_leak_current
from v2ecore.output.ae_text_output import DVSTextOutput
from v2ecore.output.aedat2_output import AEDat2Output
from v2ecore.v2e_utils import checkAddSuffix, v2e_quit, video_writer

# import rosbag # not yet for python 3

logger = logging.getLogger(__name__)


class EventEmulator(object):
    """compute events based on the input frame.
    - author: Zhe He
    - contact: zhehe@student.ethz.ch
    """

    # frames that can be displayed and saved to video
    gr=(0,255)
    l255=np.log(255)
    lg=(0,l255)
    slg=(-l255/8,l255/8)

    MODEL_STATES = {'new_frame':gr, 'lp_log_frame0':lg,
                    'lp_log_frame1':lg, 'cs_surround_frame':lg,
                    'c_minus_s_frame':slg, 'base_log_frame':slg, 'diff_frame':slg}

    MAX_CHANGE_TO_TERMINATE_EULER_SURROUND_STEPPING = 1e-5

    def __init__(
            self,
            pos_thres: float = 0.2,
            neg_thres: float = 0.2,
            sigma_thres: float = 0.03,
            cutoff_hz: float = 0.0,
            leak_rate_hz: float = 0.1,
            refractory_period_s: float = 0.0,
            shot_noise_rate_hz: float = 0.0,  # rate in hz of temporal noise events
            leak_jitter_fraction: float = 0.1,
            noise_rate_cov_decades: float = 0.1,
            seed: int = 0,
            output_folder: str = None,
            dvs_h5: str = None,
            dvs_aedat2: str = None,
            dvs_text: str = None,
            # change as you like to see 'baseLogFrame',
            # 'lpLogFrame', 'diff_frame'
            show_dvs_model_state: str = None,
            save_dvs_model_state: bool = False,
            output_width: int = None,
            output_height: int = None,
            device: str = "cuda",
            cs_lambda_pixels: float = None,
            cs_tau_p_ms: float = None
    ):
        """
        Parameters
        ----------
        pos_thres: float, default 0.21
            nominal threshold of triggering positive event in log intensity.
        neg_thres: float, default 0.17
            nominal threshold of triggering negative event in log intensity.
        sigma_thres: float, default 0.03
            std deviation of threshold in log intensity.
        cutoff_hz: float,
            3dB cutoff frequency in Hz of DVS photoreceptor
        leak_rate_hz: float
            leak event rate per pixel in Hz,
            from junction leakage in reset switch
        shot_noise_rate_hz: float
            shot noise rate in Hz
        seed: int, default=0
            seed for random threshold variations,
            fix it to nonzero value to get same mismatch every time
        dvs_aedat2, dvs_h5, dvs_text: str
            names of output data files or None
        show_dvs_model_state: List[str],
            None or 'new_frame' 'baseLogFrame','lpLogFrame0','lpLogFrame1',
            'diff_frame' etc
        output_folder: str
            Path to optional model state videos
        output_width: int,
            width of output in pixels
        output_height: int,
            height of output in pixels
        device: str
            device, either 'cpu' or 'cuda' (selected automatically by caller depending on GPU availability)
        cs_lambda_pixels: float
            space constant of surround in pixels, or None to disable surround inhibition
        cs_tau_p_ms: float
            time constant of lowpass filter of surround in ms or 0 to make surround 'instantaneous'
        """

        logger.info(
            "ON/OFF log_e temporal contrast thresholds: "
            "{} / {} +/- {}".format(pos_thres, neg_thres, sigma_thres))

        self.reset()
        self.t_previous = 0  # time of previous frame

        self.dont_show_list = []  # list of frame types to not show and not print warnings for except for once
        self.show_list = []  # list of named windows shown for internal states
        # torch device
        self.device = device

        # thresholds
        self.sigma_thres = sigma_thres
        # initialized to scalar, later overwritten by random value array
        self.pos_thres = pos_thres
        # initialized to scalar, later overwritten by random value array
        self.neg_thres = neg_thres
        self.pos_thres_nominal = pos_thres
        self.neg_thres_nominal = neg_thres

        # non-idealities
        self.cutoff_hz = cutoff_hz
        self.leak_rate_hz = leak_rate_hz
        self.refractory_period_s = refractory_period_s
        self.shot_noise_rate_hz = shot_noise_rate_hz

        self.leak_jitter_fraction = leak_jitter_fraction
        self.noise_rate_cov_decades = noise_rate_cov_decades

        self.SHOT_NOISE_INTEN_FACTOR = 0.25

        # output properties
        self.output_folder = output_folder
        self.output_width = output_width
        self.output_height = output_height  # set on first frame
        self.show_dvs_model_state = show_dvs_model_state
        self.save_dvs_model_state = save_dvs_model_state
        self.video_writers: dict[str, video_writer] = {}  # list of avi file writers for saving model state videos

        # generate jax key for random process
        if seed != 0:
            torch.manual_seed(seed)
            np.random.seed(seed)
            random.seed(seed)

        # h5 output
        self.output_folder = output_folder
        self.dvs_h5 = dvs_h5
        self.dvs_h5_dataset = None
        self.frame_h5_dataset = None
        self.frame_ts_dataset = None
        self.frame_ev_idx_dataset = None

        # aedat or text output
        self.dvs_aedat2 = dvs_aedat2
        self.dvs_text = dvs_text

        # event stats
        self.num_events_total = 0
        self.num_events_on = 0
        self.num_events_off = 0
        self.frame_counter = 0

        # csdvs
        self.cs_steps_warning_printed = False
        self.cs_steps_taken = []
        self.cs_alpha_warning_printed = False
        self.cs_tau_p_ms = cs_tau_p_ms
        self.cs_lambda_pixels = cs_lambda_pixels
        self.cs_surround_frame: Optional[torch.Tensor] = None  # surround frame state
        self.csdvs_enabled = False  # flag to run center surround DVS emulation
        if self.cs_lambda_pixels is not None:
            self.csdvs_enabled = True
            # prepare kernels
            self.cs_tau_h_ms = 0 \
                if (self.cs_tau_p_ms is None or self.cs_tau_p_ms == 0) \
                else self.cs_tau_p_ms / (self.cs_lambda_pixels ** 2)
            lat_res = 1 / (self.cs_lambda_pixels ** 2)
            trans_cond = 1 / self.cs_lambda_pixels
            logger.debug(
                f'lateral resistance R={lat_res:.2g}Ohm, transverse transconductance g={trans_cond:.2g} Siemens, Rg={(lat_res * trans_cond):.2f}')
            self.cs_k_hh = torch.tensor([[[[0, 1, 0],
                                           [1, -4, 1],
                                           [0, 1, 0]]]], dtype=torch.float32).to(self.device)
            # self.cs_k_pp = torch.tensor([[[[0, 0, 0],
            #                                [0, 1, 0],
            #                                [0, 0, 0]]]], dtype=torch.float32).to(self.device)
            logger.info(f'Center-surround parameters:\n\t'
                        f'cs_tau_p_ms: {self.cs_tau_p_ms}\n\t'
                        f'cs_tau_h_ms:  {self.cs_tau_h_ms}\n\t'
                        f'cs_lambda_pixels:  {self.cs_lambda_pixels:.2f}\n\t'
                        )

        try:
            if dvs_h5:
                path = os.path.join(self.output_folder, dvs_h5)
                path = checkAddSuffix(path, '.h5')
                logger.info('opening event output dataset file ' + path)
                self.dvs_h5 = h5py.File(path, "w")

                # for events
                self.dvs_h5_dataset = self.dvs_h5.create_dataset(
                    name="events",
                    shape=(0, 4),
                    maxshape=(None, 4),
                    dtype="uint32",
                    compression="gzip")

            if dvs_aedat2:
                path = os.path.join(self.output_folder, dvs_aedat2)
                path = checkAddSuffix(path, '.aedat')
                logger.info('opening AEDAT-2.0 output file ' + path)
                self.dvs_aedat2 = AEDat2Output(
                    path, output_width=self.output_width,
                    output_height=self.output_height)
            if dvs_text:
                path = os.path.join(self.output_folder, dvs_text)
                path = checkAddSuffix(path, '.txt')
                logger.info('opening text DVS output file ' + path)
                self.dvs_text = DVSTextOutput(path)



        except Exception as e:
            logger.error(f'Output file exception "{e}" (maybe you need to specify a supported DVS camera type?)')
            raise e

        self.screen_width = 1600
        self.screen_height = 1200
        try:
            mi = get_monitors()
            for m in mi:
                if m.is_primary:
                    self.screen_width = int(m.width)
                    self.screen_height = int(m.height)
        except Exception as e:
            logger.warning(f'cannot get screen size for window placement: {e}')

        if self.show_dvs_model_state is not None and len(self.show_dvs_model_state) == 1 and self.show_dvs_model_state[0] == 'all':
            logger.info(f'will show all model states that exist from {EventEmulator.MODEL_STATES.keys()}')
            self.show_dvs_model_state = EventEmulator.MODEL_STATES.keys()

        self.show_norms={} # dict of named tuples (min,max) for each displayed model state that adapts to fit displayed values into 0-1 range for rendering

        atexit.register(self.cleanup)

    def prepare_storage(self, n_frames, frame_ts):
        # extra prepare for frame storage
        if self.dvs_h5:
            # for frame
            self.frame_h5_dataset = self.dvs_h5.create_dataset(
                name="frame",
                shape=(n_frames, self.output_height, self.output_width),
                dtype="uint8",
                compression="gzip")

            frame_ts_arr = np.array(frame_ts, dtype=np.float32) * 1e6
            self.frame_ts_dataset = self.dvs_h5.create_dataset(
                name="frame_ts",
                shape=(n_frames,),
                data=frame_ts_arr.astype(np.uint32),
                dtype="uint32",
                compression="gzip")
            # corresponding event idx
            self.frame_ev_idx_dataset = self.dvs_h5.create_dataset(
                name="frame_idx",
                shape=(n_frames,),
                dtype="uint64",
                compression="gzip")
        else:
            self.frame_h5_dataset = None
            self.frame_ts_dataset = None
            self.frame_ev_idx_dataset = None

    def cleanup(self):
        if len(self.cs_steps_taken) > 1:
            mean_staps = np.mean(self.cs_steps_taken)
            std_steps = np.std(self.cs_steps_taken)
            median_steps = np.median(self.cs_steps_taken)
            logger.info(
                f'CSDVS steps statistics: mean+std= {mean_staps:.0f} + {std_steps:.0f} (median= {median_steps:.0f})')
        if self.dvs_h5 is not None:
            self.dvs_h5.close()

        if self.dvs_aedat2 is not None:
            self.dvs_aedat2.close()

        if self.dvs_text is not None:
            try:
                self.dvs_text.close()
            except:
                pass

        for vw in self.video_writers:
            logger.info(f'closing video AVI {vw}')
            self.video_writers[vw].release()

    def _init(self, first_frame_linear):
        """

        Parameters:
        ----------
        first_frame_linear: np.ndarray
            the first frame, used to initialize data structures

        Returns:
            new instance
        -------

        """
        logger.debug(
            'initializing random temporal contrast thresholds '
            'from from base frame')
        # base_frame are memorized lin_log pixel values
        self.diff_frame = None

        # take the variance of threshold into account.
        if self.sigma_thres > 0:
            self.pos_thres = torch.normal(
                self.pos_thres, self.sigma_thres,
                size=first_frame_linear.shape,
                dtype=torch.float32).to(self.device)

            # to avoid the situation where the threshold is too small.
            self.pos_thres = torch.clamp(self.pos_thres, min=0.01)

            self.neg_thres = torch.normal(
                self.neg_thres, self.sigma_thres,
                size=first_frame_linear.shape,
                dtype=torch.float32).to(self.device)
            self.neg_thres = torch.clamp(self.neg_thres, min=0.01)

        # compute variable for shot-noise
        self.pos_thres_pre_prob = torch.div(
            self.pos_thres_nominal, self.pos_thres)
        self.neg_thres_pre_prob = torch.div(
            self.neg_thres_nominal, self.neg_thres)

        # If leak is non-zero, then initialize each pixel memorized value
        # some fraction of ON threshold below first frame value, to create leak
        # events from the start; otherwise leak would only gradually
        # grow over time as pixels spike.
        # do this *AFTER* we determine randomly distributed thresholds
        # (and use the actual pixel thresholds)
        # otherwise low threshold pixels will generate
        # a burst of events at the first frame
        if self.leak_rate_hz > 0:
            # no justification for this subtraction after having the
            # new leak rate model
            #  self.base_log_frame -= torch.rand(
            #      first_frame_linear.shape,
            #      dtype=torch.float32, device=self.device)*self.pos_thres

            # set noise rate array, it's a log-normal distribution
            self.noise_rate_array = torch.randn(
                first_frame_linear.shape, dtype=torch.float32,
                device=self.device)
            self.noise_rate_array = torch.exp(
                math.log(10) * self.noise_rate_cov_decades * self.noise_rate_array)

        # refractory period
        if self.refractory_period_s > 0:
            self.timestamp_mem = torch.zeros(
                first_frame_linear.shape, dtype=torch.float32,
                device=self.device) - self.refractory_period_s

    def set_dvs_params(self, model: str):
        if model == 'clean':
            self.pos_thres = 0.2
            self.neg_thres = 0.2
            self.sigma_thres = 0.02
            self.cutoff_hz = 0
            self.leak_rate_hz = 0
            self.leak_jitter_fraction = 0
            self.noise_rate_cov_decades = 0
            self.shot_noise_rate_hz = 0  # rate in hz of temporal noise events
            self.refractory_period_s = 0

        elif model == 'noisy':
            self.pos_thres = 0.2
            self.neg_thres = 0.2
            self.sigma_thres = 0.05
            self.cutoff_hz = 30
            self.leak_rate_hz = 0.1
            # rate in hz of temporal noise events
            self.shot_noise_rate_hz = 5.0
            self.refractory_period_s = 0
            self.leak_jitter_fraction = 0.1
            self.noise_rate_cov_decades = 0.1
        else:
            #  logger.error(
            #      "dvs_params {} not known: "
            #      "use 'clean' or 'noisy'".format(model))
            logger.warning(
                "dvs_params {} not known: "
                "Using commandline assigned options".format(model))
            #  sys.exit(1)
        logger.info("set DVS model params with option '{}' "
                    "to following values:\n"
                    "pos_thres={}\n"
                    "neg_thres={}\n"
                    "sigma_thres={}\n"
                    "cutoff_hz={}\n"
                    "leak_rate_hz={}\n"
                    "shot_noise_rate_hz={}\n"
                    "refractory_period_s={}".format(
            model, self.pos_thres, self.neg_thres,
            self.sigma_thres, self.cutoff_hz,
            self.leak_rate_hz, self.shot_noise_rate_hz,
            self.refractory_period_s))

    def reset(self):
        '''resets so that next use will reinitialize the base frame
        '''
        self.num_events_total = 0
        self.num_events_on = 0
        self.num_events_off = 0

        # add names of new states to potentially show with --show_model_states all
        self.new_frame: Optional[np.ndarray] = None
        self.lp_log_frame0: Optional[np.ndarray] = None  # lowpass stage 0
        self.lp_log_frame1: Optional[np.ndarray] = None  # stage 1
        self.cs_surround_frame: Optional[np.ndarray] = None
        self.c_minus_s_frame: Optional[np.ndarray] = None
        self.base_log_frame: Optional[np.ndarray] = None
        self.diff_frame: Optional[np.ndarray] = None

        self.frame_counter = 0

    def _show(self, inp: torch.Tensor, name: str):
        """
        Shows the ndarray in window, and save frame to avi file if self.save_dvs_model_state==True.
        The displayed image is normalized according to its type (grayscale, log, or signed log).
        Parameters
        ----------
        inp: the array
        name: label for window

        Returns
        -------
        None
        """

        img = np.array(inp.cpu().data.numpy())
        (min,max)=EventEmulator.MODEL_STATES[name]

        img=(img-min)/(max-min)

        cv2.namedWindow(name, cv2.WINDOW_NORMAL)
        if not name in self.show_list:
            d = len(self.show_list) * 200
            # (x,y,w,h)=cv2.getWindowImageRect(name)
            cv2.moveWindow(name, int(self.screen_width / 8 + d), int(self.screen_height / 8 + d / 2))
            self.show_list.append(name)
            if self.save_dvs_model_state:
                fn = os.path.join(self.output_folder, name + '.avi')
                vw = video_writer(fn, self.output_height, self.output_width)
                self.video_writers[name] = vw
        cv2.putText(img,f'fr:{self.frame_counter} t:{self.t_previous:.4f}s', org=(0,self.output_height),fontScale=1.5, color=(0,0,0), fontFace=cv2.FONT_HERSHEY_PLAIN, thickness=2)
        cv2.imshow(name, img)
        if self.save_dvs_model_state:
            self.video_writers[name].write(
                cv2.cvtColor((img * 255).astype(np.uint8),
                             cv2.COLOR_GRAY2BGR))

    def generate_events(self, new_frame, t_frame):
        """Compute events in new frame.

        Parameters
        ----------
        new_frame: np.ndarray
            [height, width], NOTE y is first dimension, like in matlab the column, x is 2nd dimension, i.e. row.
        t_frame: float
            timestamp of new frame in float seconds

        Returns
        -------
        events: np.ndarray if any events, else None
            [N, 4], each row contains [timestamp, y coordinate,
            x coordinate, sign of event].
            NOTE y then x, not x,y.
        """

        # base_frame: the change detector input,
        #              stores memorized brightness values
        # new_frame: the new intensity frame input
        # log_frame: the lowpass filtered brightness values

        # like a DAVIS, write frame into the file if it's HDF5
        if self.frame_h5_dataset is not None:
            # save frame data
            self.frame_h5_dataset[self.frame_counter] = \
                new_frame.astype(np.uint8)

        # update frame counter
        self.frame_counter += 1

        if t_frame < self.t_previous:
            raise ValueError(
                "this frame time={} must be later than "
                "previous frame time={}".format(t_frame, self.t_previous))

        # compute time difference between this and the previous frame
        delta_time = t_frame - self.t_previous
        # logger.debug('delta_time={}'.format(delta_time))

        # convert into torch tensor
        self.new_frame = torch.tensor(new_frame, dtype=torch.float64,
                                      device=self.device)
        # lin-log mapping
        log_new_frame = lin_log(self.new_frame)

        inten01 = None  # define for later
        if self.cutoff_hz > 0 or self.shot_noise_rate_hz > 0:  # will use later
            # Time constant of the filter is proportional to
            # the intensity value (with offset to deal with DN=0)
            # limit max time constant to ~1/10 of white intensity level
            inten01 = rescale_intensity_frame(self.new_frame.clone().detach())  # TODO assumes 8 bit

        # Apply nonlinear lowpass filter here.
        # Filter is a 1st order lowpass IIR (can be 2nd order)
        # that uses two internal state variables
        # to store stages of cascaded first order RC filters.
        # Time constant of the filter is proportional to
        # the intensity value (with offset to deal with DN=0)
        if self.base_log_frame is None:
            # initialize first stage of 2nd order IIR to first input
            self.lp_log_frame0 = log_new_frame
            # 2nd stage is initialized to same,
            # so diff will be zero for first frame
            self.lp_log_frame1 = log_new_frame
        self.lp_log_frame0, self.lp_log_frame1 = low_pass_filter(
            log_new_frame=log_new_frame,
            lp_log_frame0=self.lp_log_frame0,
            lp_log_frame1=self.lp_log_frame1,
            inten01=inten01,
            delta_time=delta_time,
            cutoff_hz=self.cutoff_hz)

        # surround computations by time stepping the diffuser
        if self.csdvs_enabled:
            self._update_csdvs(delta_time)

        if self.base_log_frame is None:
            self._init(new_frame)
            if not self.csdvs_enabled:
                self.base_log_frame = self.lp_log_frame1
            else:
                self.base_log_frame = self.lp_log_frame1 - self.cs_surround_frame  # init base log frame (input to diff) to DC value, TODO check might not be correct to avoid transient

            return None  # on first input frame we just setup the state of all internal nodes of pixels

        # Leak events: switch in diff change amp leaks at some rate
        # equivalent to some hz of ON events.
        # Actual leak rate depends on threshold for each pixel.
        # We want nominal rate leak_rate_Hz, so
        # R_l=(dI/dt)/Theta_on, so
        # R_l*Theta_on=dI/dt, so
        # dI=R_l*Theta_on*dt
        if self.leak_rate_hz > 0:
            self.base_log_frame = subtract_leak_current(
                base_log_frame=self.base_log_frame,
                leak_rate_hz=self.leak_rate_hz,
                delta_time=delta_time,
                pos_thres=self.pos_thres,
                leak_jitter_fraction=self.leak_jitter_fraction,
                noise_rate_array=self.noise_rate_array)

        # log intensity (brightness) change from memorized values is computed
        # from the difference between new input
        # (from lowpass of lin-log input) and the memorized value
        if not self.csdvs_enabled:
            self.diff_frame = self.lp_log_frame1 - self.base_log_frame
        else:
            self.c_minus_s_frame = self.lp_log_frame1 - self.cs_surround_frame
            self.diff_frame = self.c_minus_s_frame - self.base_log_frame

        if not self.show_dvs_model_state is None:
            for s in self.show_dvs_model_state:
                if not s in self.dont_show_list:
                    f = getattr(self, s, None)
                    if f is None:
                        logger.error(f'{s} does not exist so we cannot show it')
                        self.dont_show_list.append(s)
                    else:
                        self._show(f, s) # show the frame f with name s
            k = cv2.waitKey(30)
            if k == 27 or k == ord('x'):
                v2e_quit()

        # generate event map
        pos_evts_frame, neg_evts_frame = compute_event_map(
            self.diff_frame, self.pos_thres, self.neg_thres)
        pos_num_iters = pos_evts_frame.max().square()
        neg_num_iters = neg_evts_frame.max().square()

        # record final events update
        final_pos_evts_frame = torch.zeros(
            pos_evts_frame.shape, dtype=torch.int32, device=self.device)
        final_neg_evts_frame = torch.zeros(
            neg_evts_frame.shape, dtype=torch.int32, device=self.device)

        # update the base frame, after we know how many events per pixel
        # add to memorized brightness values just the events we emitted.
        # don't add the remainder.
        # the next aps frame might have sufficient value to trigger
        # another event or it might not, but we are correct in not storing
        # the current frame brightness
        #  self.base_log_frame += pos_evts_frame*self.pos_thres
        #  self.base_log_frame -= neg_evts_frame*self.neg_thres

        # all events
        events = []

        zero_tensor = torch.tensor(0, dtype=torch.int32)

        # ******************************************************
        # positive events generation
        # ******************************************************
        pos_ts_step = delta_time / pos_num_iters
        pos_ts = torch.linspace(
            start=self.t_previous + pos_ts_step,
            end=t_frame,
            steps=pos_num_iters, dtype=torch.float32, device=self.device)

        if self.shot_noise_rate_hz > 0:
            shot_on_cord, _ = generate_shot_noise(
                shot_noise_rate_hz=self.shot_noise_rate_hz,
                delta_time=delta_time,
                num_iters=pos_num_iters,
                shot_noise_inten_factor=self.SHOT_NOISE_INTEN_FACTOR,
                inten01=inten01,
                pos_thres_pre_prob=self.pos_thres_pre_prob,
                neg_thres_pre_prob=zero_tensor)

        print('************ pos: {} ****************'.format(pos_num_iters))
        pos_evts_frame_without_zeros = torch.where(pos_evts_frame == zero_tensor, pos_num_iters + 1,
                                                   pos_evts_frame)
        pos_evts_frame_uniform_interval = torch.div(pos_num_iters, pos_evts_frame_without_zeros,
                                                    rounding_mode="floor").type(torch.int32)
        pos_evts_frame_uniform = pos_evts_frame_uniform_interval

        for i in range(pos_num_iters):
            pos_events_curr_iter = None

            # uniform method
            pos_cord = (pos_evts_frame_uniform == i + 1)

            pos_evts_frame_uniform = pos_evts_frame_uniform + pos_cord * pos_evts_frame_uniform_interval

            if self.shot_noise_rate_hz > 0:
                pos_cord = torch.logical_or(pos_cord, shot_on_cord[i])

            if self.refractory_period_s > pos_ts_step:
                pos_time_since_last_spike = (pos_cord * pos_ts[i] - self.timestamp_mem)

                pos_cord = (pos_time_since_last_spike > self.refractory_period_s)

                self.timestamp_mem = torch.where(pos_cord, pos_ts[i], self.timestamp_mem)

            final_pos_evts_frame += pos_cord

            pos_event_xy = pos_cord.nonzero(as_tuple=True)

            num_pos_events = pos_event_xy[0].shape[0]

            # show the percentage
            print('----- {} : {} -----'.format(i + 1, num_pos_events))

            self.num_events_on += num_pos_events
            # self.num_events_total += num_events

            if num_pos_events > 0:
                pos_events_curr_iter = torch.ones(
                    (num_pos_events, 4), dtype=torch.float32,
                    device=self.device)
                pos_events_curr_iter[:, 0] *= pos_ts[i]

                pos_events_curr_iter[:num_pos_events, 1] = pos_event_xy[1]
                pos_events_curr_iter[:num_pos_events, 2] = pos_event_xy[0]

                pos_events_curr_iter[:num_pos_events, 3] *= 1

            # shuffle and append to the events collectors
            if pos_events_curr_iter is not None:
                idx = torch.randperm(pos_events_curr_iter.shape[0])
                pos_events_curr_iter = pos_events_curr_iter[idx].view(
                    pos_events_curr_iter.size())
                events.append(pos_events_curr_iter)

        # ******************************************************
        # negative events generation
        # ******************************************************
        neg_ts_step = delta_time / neg_num_iters
        neg_ts = torch.linspace(
            start=self.t_previous + neg_ts_step,
            end=t_frame,
            steps=neg_num_iters, dtype=torch.float32, device=self.device)

        if self.shot_noise_rate_hz > 0:
            _, shot_off_cord = generate_shot_noise(
                shot_noise_rate_hz=self.shot_noise_rate_hz,
                delta_time=delta_time,
                num_iters=neg_num_iters,
                shot_noise_inten_factor=self.SHOT_NOISE_INTEN_FACTOR,
                inten01=inten01,
                pos_thres_pre_prob=zero_tensor,
                neg_thres_pre_prob=self.neg_thres_pre_prob)

        print('************ neg: {} ****************'.format(neg_num_iters))
        neg_evts_frame_without_zeros = torch.where(neg_evts_frame == zero_tensor, neg_num_iters + 1,
                                                   neg_evts_frame)
        neg_evts_frame_uniform_interval = torch.div(neg_num_iters, neg_evts_frame_without_zeros,
                                                    rounding_mode="floor").type(torch.int32)
        neg_evts_frame_uniform = neg_evts_frame_uniform_interval

        for i in range(neg_num_iters):
            neg_events_curr_iter = None

            # uniform method
            neg_cord = (neg_evts_frame_uniform == i + 1)

            neg_evts_frame_uniform = neg_evts_frame_uniform + neg_cord * neg_evts_frame_uniform_interval

            if self.shot_noise_rate_hz > 0:
                neg_cord = torch.logical_or(neg_cord, shot_off_cord[i])

            if self.refractory_period_s > neg_ts_step:
                neg_time_since_last_spike = (neg_cord * neg_ts[i] - self.timestamp_mem)

                neg_cord = (neg_time_since_last_spike > self.refractory_period_s)

                self.timestamp_mem = torch.where(neg_cord, neg_ts[i], self.timestamp_mem)

            final_neg_evts_frame += neg_cord

            neg_event_xy = neg_cord.nonzero(as_tuple=True)

            num_neg_events = neg_event_xy[0].shape[0]

            # show the percentage
            print('----- {} : {} -----'.format(i + 1, num_neg_events))

            self.num_events_off += num_neg_events

            if num_neg_events > 0:
                neg_events_curr_iter = torch.ones(
                    (num_neg_events, 4), dtype=torch.float32,
                    device=self.device)
                neg_events_curr_iter[:, 0] *= neg_ts[i]

                neg_events_curr_iter[:num_neg_events, 1] = neg_event_xy[1]
                neg_events_curr_iter[:num_neg_events, 2] = neg_event_xy[0]

                neg_events_curr_iter[:num_neg_events, 3] *= -1

            # shuffle and append to the events collectors
            if neg_events_curr_iter is not None:
                idx = torch.randperm(neg_events_curr_iter.shape[0])
                neg_events_curr_iter = neg_events_curr_iter[idx].view(
                    neg_events_curr_iter.size())
                events.append(neg_events_curr_iter)

        # sort
        if len(events) > 0:
            events = torch.vstack(events)
            events = events[events[:, 0].sort()[1]]
            # print(events.shape)

        num_events = self.num_events_on + self.num_events_off
        self.num_events_total += num_events

        # update base log frame according to the final
        # number of output events
        self.base_log_frame += final_pos_evts_frame * self.pos_thres
        self.base_log_frame -= final_neg_evts_frame * self.neg_thres

        if len(events) > 0:
            events = events.cpu().data.numpy()
            if self.dvs_h5 is not None:
                # convert data to uint32 (microsecs) format
                temp_events = np.array(events, dtype=np.float32)
                temp_events[:, 0] = temp_events[:, 0] * 1e6
                temp_events[temp_events[:, 3] == -1, 3] = 0
                temp_events = temp_events.astype(np.uint32)

                # save events
                self.dvs_h5_dataset.resize(
                    self.dvs_h5_dataset.shape[0] + temp_events.shape[0],
                    axis=0)

                self.dvs_h5_dataset[-temp_events.shape[0]:] = temp_events

            if self.dvs_aedat2 is not None:
                self.dvs_aedat2.appendEvents(events)
            if self.dvs_text is not None:
                self.dvs_text.appendEvents(events)

        if self.frame_ev_idx_dataset is not None:
            # save frame event idx
            # determine after the events are added
            self.frame_ev_idx_dataset[self.frame_counter - 1] = \
                self.dvs_h5_dataset.shape[0]

        # assign new time
        self.t_previous = t_frame
        if len(events) > 0:
            return events
        else:
            return None

    def _update_csdvs(self, delta_time):
        if self.cs_surround_frame is None:
            self.cs_surround_frame = self.lp_log_frame1.clone().detach()  # detach makes true clone decoupled from torch computation tree
        else:
            # we still need to simulate dynamics even if "instantaneous", unfortunately it will be really slow with Euler stepping and
            # no gear-shifting
            # TODO change to compute steady-state 'instantaneous' solution by better method than Euler stepping
            abs_min_tau_p = 1e-9
            tau_p = abs_min_tau_p if (
                    self.cs_tau_p_ms is None or self.cs_tau_p_ms == 0) else self.cs_tau_p_ms * 1e-3
            tau_h = abs_min_tau_p / (self.cs_lambda_pixels ** 2) if (
                    self.cs_tau_h_ms is None or self.cs_tau_h_ms == 0) else self.cs_tau_h_ms * 1e-3
            min_tau = min(tau_p, tau_h)
            # if min_tau < abs_min_tau_p:
            #     min_tau = abs_min_tau_p
            NUM_STEPS_PER_TAU = 5
            num_steps = int(np.ceil((delta_time / min_tau) * NUM_STEPS_PER_TAU))
            actual_delta_time = delta_time / num_steps
            if num_steps > 1000 and not self.cs_steps_warning_printed:
                if self.cs_tau_p_ms==0:
                    logger.warning(f'You set time constant cs_tau_p_ms to zero which set the minimum tau of {abs_min_tau_p}s')
                logger.warning(
                    f'CSDVS timestepping of diffuser could take up to {num_steps} '
                    f'steps per frame for Euler delta time {actual_delta_time:.3g}s; '
                    f'simulation of each frame will terminate when max change is smaller than {EventEmulator.MAX_CHANGE_TO_TERMINATE_EULER_SURROUND_STEPPING}')
                self.cs_steps_warning_printed = True

            alpha_p = actual_delta_time / tau_p
            alpha_h = actual_delta_time / tau_h
            if alpha_p >= 1 or alpha_h >= 1:
                logger.error(
                    f'CSDVS update alpha (of IIR update) is too large; simulation would explode: '
                    f'alpha_p={alpha_p:.3f} alpha_h={alpha_h:.3f}')
                self.cs_alpha_warning_printed = True
                v2e_quit(1)
            if alpha_p > .25 or alpha_h > .25:
                logger.warning(
                    f'CSDVS update alpha (of IIR update) is too large; simulation will be inaccurate: '
                    f'alpha_p={alpha_p:.3f} alpha_h={alpha_h:.3f}')
                self.cs_alpha_warning_printed = True
            p_ten = torch.unsqueeze(torch.unsqueeze(self.lp_log_frame1, 0), 0)
            h_ten = torch.unsqueeze(torch.unsqueeze(self.cs_surround_frame, 0), 0)
            padding = torch.nn.ReplicationPad2d(1)
            max_change = 2 * EventEmulator.MAX_CHANGE_TO_TERMINATE_EULER_SURROUND_STEPPING
            steps = 0
            while steps < num_steps and max_change>EventEmulator.MAX_CHANGE_TO_TERMINATE_EULER_SURROUND_STEPPING:
                if not self.show_dvs_model_state is None and steps % 100 == 0:
                    cv2.pollKey() # allow movement of windows and resizing
                diff = p_ten - h_ten
                p_term = alpha_p * diff
                # For the conv2d, unfortunately the zero padding pulls down the border pixels,
                # so we use replication padding to reduce this effect on border.
                # TODO check if possible to implement some form of open circuit resistor termination condition by correct padding
                h_conv = torch.conv2d(padding(h_ten.float()), self.cs_k_hh.float())
                h_term = alpha_h * h_conv
                change_ten = p_term + h_term # change_ten is the change in the diffuser voltage
                max_change = torch.max(torch.abs(change_ten)).item() # find the maximum absolute change in any diffuser pixel
                h_ten += change_ten
                steps += 1

            self.cs_steps_taken.append(steps)
            self.cs_surround_frame = torch.squeeze(h_ten)


if __name__ == "__main__":
    # define a emulator
    emulator = EventEmulator(
        pos_thres=0.2,
        neg_thres=0.2,
        sigma_thres=0.03,
        cutoff_hz=200,
        leak_rate_hz=1,
        shot_noise_rate_hz=10,
        device="cuda",
    )

    cap = cv2.VideoCapture(
        os.path.join(os.environ["HOME"], "v2e_tutorial_video.avi"))

    # num of frames
    fps = cap.get(cv2.CAP_PROP_FPS)
    print("FPS: {}".format(fps))
    num_of_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("Num of frames: {}".format(num_of_frames))

    duration = num_of_frames / fps
    delta_t = 1 / fps
    current_time = 0.

    print("Clip Duration: {}s".format(duration))
    print("Delta Frame Tiem: {}s".format(delta_t))
    print("=" * 50)

    new_events = None

    idx = 0
    # Only Emulate the first 10 frame
    while cap.isOpened():
        # Capture frame-by-frame
        ret, frame = cap.read()
        if ret is True and idx < 10:
            # convert it to Luma frame
            luma_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            print("=" * 50)
            print("Current Frame {} Time {}".format(idx, current_time))
            print("-" * 50)

            # # emulate events
            new_events = emulator.generate_events(luma_frame, current_time)

            # update time
            current_time += delta_t

            # print event stats
            if new_events is not None:
                num_events = new_events.shape[0]
                start_t = new_events[0, 0]
                end_t = new_events[-1, 0]
                event_time = (new_events[-1, 0] - new_events[0, 0])
                event_rate_kevs = (num_events / delta_t) / 1e3

                print("Number of Events: {}\n"
                      "Duration: {}\n"
                      "Start T: {:.5f}\n"
                      "End T: {:.5f}\n"
                      "Event Rate: {:.2f}KEV/s".format(
                    num_events, event_time, start_t, end_t,
                    event_rate_kevs))
            idx += 1
            print("=" * 50)
        else:
            break

    cap.release()
