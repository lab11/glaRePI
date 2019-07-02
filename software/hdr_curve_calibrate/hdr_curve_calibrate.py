#!/usr/bin/env python3

import os
import subprocess
import time
import gphoto2 as gp

exposures = list(range(-4, 5, 2))
template = os.path.join('./', 'frame_%s.jpg')
context = gp.Context()
camera = gp.Camera()
camera.init(context)
cfg = camera.get_config()
exposurecomp_cfg = cfg.get_child_by_name('exposurecompensation')
capturetarget_cfg = cfg.get_child_by_name('capturetarget')
capturetarget = capturetarget_cfg.get_value()
capturetarget_cfg.set_value('Internal RAM')
imageformat_cfg = cfg.get_child_by_name('imageformat')
imageformat_cfg.set_value('Small Fine JPEG')
camera.set_config(cfg)
fnames = []

if os.path.exists('testimg.tif'):
    os.remove('testimg.tif')

def empty_event_queue(camera):
    while True:
        type_, data = camera.wait_for_event(10)
        if type_ == gp.GP_EVENT_TIMEOUT:
            return
        if type_ == gp.GP_EVENT_FILE_ADDED:
            # get a second image if camera is set to raw + jpeg
            print('Unexpected new file', data.folder + data.name)

for exp in exposures:
    empty_event_queue(camera)
    exposurecomp_cfg.set_value(str(exp))
    camera.set_config(cfg)
    path = camera.capture(gp.GP_CAPTURE_IMAGE)
    camera_file = camera.file_get(path.folder, path.name, gp.GP_FILE_TYPE_NORMAL)
    camera_file.save(template % str(exp))
    fnames.append(template % str(exp))
    camera.file_delete(path.folder, path.name)

exposurecomp_cfg.set_value('0')
camera.set_config(cfg)
camera.exit()

proc = subprocess.check_call(['hdrgen'] + fnames + ['-o', 'testimg.tif', '-r', 'cam.rsp'])
