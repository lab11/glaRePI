#!/usr/bin/env python3

import os
import numpy as np 
import subprocess
import time
import datetime 
import gphoto2 as gp
import u3
import imageio
import tempfile 

# Directory organization
photos_dir = "photos/"
hdr_dir = "hdr/"
cali_hdr_dir = "calibrated_hdr/"
tifs_dir = "tifs/"

directories = [photos_dir, hdr_dir, cali_hdr_dir, tifs_dir]
for d in directories:
    if not os.path.exists(d):
        os.makedirs(d)

d = u3.U3()
template = 'frame_%s.jpg'

# Camera configuration
aperture = 8
vfrac = 0.850
shutter_cfg = None
offset = [-10, 5]

def camera_init():
    exposures = list(range(-4, 5, 2))
    context = gp.Context()
    camera = gp.Camera()
    camera.exit()
    camera.init(context)
    cfg = camera.get_config()
    cfg.get_child_by_name('imageformat').set_value('Large Fine JPEG')
    cfg.get_child_by_name('iso').set_value('100')
    cfg.get_child_by_name('aperture').set_value('8')
    cfg.get_child_by_name('whitebalance').set_value('Daylight')
    cfg.get_child_by_name('capturetarget').set_value('Internal RAM')
    cfg.get_child_by_name('imageformat').set_value('Small Fine JPEG')
    camera.set_config(cfg)
    return camera

def capture_photos(camera, lux):
    print(lux) 
    fnames = []
    cfg = camera.get_config()
    shutter_cfg = cfg.get_child_by_name('shutterspeed')
    shutters = []
    if lux > 1200:
        shutters = ['1/8000', '1/2000', '1/500', '1/125', '1/30', '1/8', '0.5'] 
    else:
        shutters = ['1/8000', '1/2000', '1/500', '1/125', '1/30', '1/8', '0.5', '2', '8'] 
    for i, shutter in enumerate(shutters):
        print('shutter: ' + shutter)
        empty_event_queue(camera)
        shutter_cfg.set_value(shutter)
        camera.set_config(cfg)
        path = camera.capture(gp.GP_CAPTURE_IMAGE)
        camera_file = camera.file_get(path.folder, path.name, gp.GP_FILE_TYPE_NORMAL)
        camera_file.save(photos_dir + (template % i)) 
        camera.file_delete(path.folder, path.name)
        fnames.append(photos_dir + (template % i))
    return fnames

def generate_hdr(fnames, lux):
    hdr_fname = hdr_dir + 'img.hdr'
    square_fname = hdr_dir + 'square.hdr'
    print("Generating HDR image")
    proc = subprocess.check_call(['hdrgen'] + fnames + ['-F', '-o', hdr_fname, '-r', 'camera_response.rsp'])
        
    # apply fisheye correction
    print("Applying fisheye lens correction")
    # get image resolution
    im = imageio.imread(hdr_fname)
    # calculate new resolution
    imgh = int(im.shape[0] * vfrac + 0.5)
    imgw = int(im.shape[1] * vfrac + 0.5)
    
    print("ra_xyze")
    with tempfile.SpooledTemporaryFile() as temp, open(square_fname, 'w') as output:
        proc = subprocess.Popen(['ra_xyze', '-r', '-o', hdr_fname], stdout=temp)
        proc.wait()
        temp.seek(0)
        proc = subprocess.Popen(['pcompos', '-x',  str(imgh), '-y', str(imgh), '=00', '-', str(int(imgh/2)+offset[0]), str(int(imgh/2)+offset[1])], stdin=temp, stdout=output)
        proc.wait()
    
    # lens correction
    lens_fname = hdr_dir + 'lens.hdr'
    print("pcomb")
    with tempfile.SpooledTemporaryFile() as temp, open(lens_fname, 'w') as output:
        proc = subprocess.Popen(['pcomb', '-f', 'fisheye_corr.cal', '-o', square_fname], stdout=temp)
        proc.wait()
        temp.seek(0)
        proc = subprocess.Popen(['getinfo', '-a', "\"VIEW= -vta -vv 180 -vh 180\""], stdin=temp, stdout=output) 
        proc.wait()
    
    # vignetting correction
    print("Applying vignetting correction")
    corrected_fname = hdr_dir + 'corrected.hdr' 
    vignette_command = """sq(x):x*x; 
td(x):tan(PI*x/180);
SigmaVig8_0(deg) : 1+0.002*td(deg*.991)-0.0001*sq(td(deg*.991));
centx=xmax/2+({}); centy=ymax/2+({});
xne=(x-centx)/(ymax/2); yne=(y-centy)/(ymax/2);
deg_cent=90*sqrt(sq(xne) + sq(yne));
corr=1.0/SigmaVig8_0(deg_cent);
ro=corr*ri(1);go=corr*gi(1);bo=corr*bi(1);""".format(offset[0], offset[1])
    
    with open('vignette_corr.cal', 'w') as f:
        f.write(vignette_command) 
    
    with tempfile.SpooledTemporaryFile() as temp:
        proc = subprocess.Popen(['pcomb', '-f', 'vignette_corr.cal', '-o', lens_fname], stdout=temp)
        proc.wait()
        temp.seek(0)
        proc = subprocess.Popen(['ra_rgbe', '-f', '-r', '-', corrected_fname], stdin=temp) 
        proc.wait()

    # get illuminance from hdr image
    print("Calibrating image against illuminance")
    camera_illuminance = 0
    with tempfile.SpooledTemporaryFile() as pcomb_t, tempfile.SpooledTemporaryFile() as pvalue_t, tempfile.SpooledTemporaryFile() as total_t: 
        proc = subprocess.Popen(['pcomb', '-f', 'illuminance_corr.cal', '-o', corrected_fname], stdout=pcomb_t)
        proc.wait()
        pcomb_t.seek(0)
        proc = subprocess.Popen(['pvalue', '-h', '-H', '-pG', '-df'], stdin=pcomb_t, stdout=pvalue_t)
        proc.wait()
        pvalue_t.seek(0)
        proc = subprocess.Popen(['total', '-if'], stdin=pvalue_t, stdout=total_t)
        proc.wait()
        total_t.seek(0)
        proc = subprocess.Popen(['rcalc', '-e', '$1=floor($1+0.5)'], stdin=total_t, stdout=subprocess.PIPE)
        proc.wait()
        result = proc.communicate()
        camera_illuminance = float(result[0].decode(encoding='utf-8'))
        print(camera_illuminance)
        
    camera_illuminance_factor = lux / camera_illuminance
    
    # Applying calibration to hdr image
    cali_fname= hdr_dir + 'cali.hdr' 
    with tempfile.SpooledTemporaryFile() as temp, open(cali_fname, 'w') as output:
        proc = subprocess.Popen(['pcomb', '-e', 'inside(x,y):if(sqrt((x-xmax/2)^2+(y-ymax/2)^2)-xmax/2,0,1)', \
	    '-e', 'ro=if(inside(x,y),ri(1),0);go=if(inside(x,y),gi(1),0); bo=if(inside(x,y),bi(1),0)', \
            '-s', str(camera_illuminance_factor), corrected_fname], stdout=temp)
        proc.wait()
        temp.seek(0)
        proc = subprocess.Popen(['ra_rgbe', '-f', '-r'], stdin=temp, stdout=output) 
        proc.wait()



def calibrate_hdr(lux):
    pass

def empty_event_queue(camera):
    while True:
        type_, data = camera.wait_for_event(10)
        if type_ == gp.GP_EVENT_TIMEOUT:
            return
        if type_ == gp.GP_EVENT_FILE_ADDED:
            # get a second image if camera is set to raw + jpeg
            print('Unexpected new file', data.folder + data.name)

camera = camera_init()
lux = d.getAIN(0) * 3.88 / 1.8 * 1000  
fnames = capture_photos(camera, lux)
lux = (lux + d.getAIN(0) * 3.88 / 1.8 * 1000)/2
generate_hdr(fnames, lux)
result = subprocess.check_output(["evalglare", "-vta", "-vv", "180", "-vh", "180", "-i", "{:.2f}".format(lux), "hdr/cali.hdr"]).decode('utf-8').strip()
names = result.split(':')[0].split(',')
values = result.split(':')[-1].strip().split(' ')
print(values)

exit()

with open("data.csv", 'a+') as f:
    nowtime = [datetime.datetime.now().isoformat()]
    lux = 0
    for exp in exposures:
        lux += d.getAIN(0) / len(exposures)
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
    lux = lux * 3.88 / 1.8 * 1000
    print('lux: ' + str(lux)) 
    try: 
        #proc = subprocess.check_call(['hdrgen'] + fnames + ['-F', '-o', 'testimg.tif', '-r', 'cam.rsp'])
        proc = subprocess.check_call(['hdrgen'] + fnames + ['-F', '-o', 'testimg.hdr', '-r', 'cam.rsp'])
        proc = subprocess.check_call(["convert","testimg.hdr", "-resize", "1100^>", "-gravity", "center", "-crop", "1000x1000+0+0", "-strip", "testimg.hdr"])
        result = subprocess.check_output(["evalglare", "-vta", "-vv", "180", "-vh", "180", "-i", "{:.2f}".format(lux), "testimg.hdr"]).decode('utf-8').strip()
        
        names = result.split(':')[0].split(',')
        values = result.split(':')[-1].strip().split(' ')
        print(values)
        if(f.tell() == 0): 
            f.write(",".join(names)+'\n')
        f.write(",".join(nowtime+values)+'\n')
        #result = {}
        #for n,v in zip(names, values):
        #    result[n] = float(v)
    except:
        print("there was an error using evalglare")
    
