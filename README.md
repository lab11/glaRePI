# glaRePI
Implementation of [radiance](https://www.radiance-online.org/) glare metric
calculation on Raspberry PI

## Required hardware:
- **DSLR camera.** I'm using a Cannon T3i, Folks at LBNL use the Cannon D60. Any
APS-C frame interchangeable DSLR camera with gphoto2 compatability, exposure adjustment,
and aperature and shutter control should work.
- **Camera AC adapter.** Allows you to power your camera from an outlet. Ensure you get the correct version for your camera. This one works nicely for the [T3i](https://www.amazon.com/gp/product/B0092F974E/) and for the [D60](https://shop.usa.canon.com/shop/en/catalog/ac-adapter-kit-ack-e6)
- **Fisheye Lens.** The standard is the [Sigma 4.5mm F2.8 EX DC
HSM](https://www.sigma-global.com/en/lenses/others/wide/45_28/).
- **Raspberry Pi.** I'm using a [model 3B+](https://www.raspberrypi.org/products/raspberry-pi-3-model-b-plus/).
- **LI-COR LI210 Photometer.** Eye-level vertical illumance sensor. Can be purchased from [EME Systems](https://emesystems.com/licor/buy.html).
- **LI-COR Hot Shoe Mount.** The LI-COR sensor needs to be mounted as close to the camera lens as possible to measure vertical illumance. A hot shoe mount can be 3D printed from the STL models in the [`hardware/licor-mount` directory](https://github.com/lab11/glaRePI/tree/master/hardware/licor-mount).
- **UTA (Universal Transconductance Amplifier).** Amplifies signal from LI-COR
sensor to be used by a data logger. Can also be purchased from [EME
Systems](https://emesystems.com/uta/main.html). Order the 2.5V (HOBO) output.
It doesn't really matter which voltage you choose, because the output
can be changed with dip switches.
- **LabJack U3-HV logger.** A [labjack data
logger](https://labjack.com/products/u3) to collect readings from the light
sensor.

## Installation Guide
First, perform a fresh install of
[Raspbian](https://www.raspberrypi.org/downloads/raspbian/). As of this
writing, Raspbian is based off of Debian Buster, and these instructions assume
this release.

Next, install required software:

### Install python3, pip, gphoto2, imagemagick, ffmpeg and other required packages:
```
sudo apt install python3 python3-pip python-pip libgphoto2-dev imagemagick ffmpeg libusb-1.0-0.dev build-essential xdg-utils libx11-dev libxext-dev libxfixes-dev libxi-dev libxrender-dev libxcb1-dev libx11-xcb-dev libxcb-glx0-dev xutils csh git vim
```

### Install hdrgen:
Need to install older version of openexr
```
wget http://ftp.us.debian.org/debian/pool/main/o/openexr/libopenexr-dev_2.2.0-11+b1_armhf.deb
wget http://ftp.us.debian.org/debian/pool/main/o/openexr/libopenexr22_2.2.0-11+b1_armhf.deb
wget http://ftp.us.debian.org/debian/pool/main/i/ilmbase/libilmbase12_2.2.0-12_armhf.deb
sudo dpkg -i libilmbase12_2.2.0-12_armhf.deb
sudo dpkg -i libopenexr22_2.2.0-11+b1_armhf.deb
sudo dpkg -i libopenexr-dev_2.2.0-11+b1_armhf.deb
rm *.deb
wget http://www.anyhere.com/gward/pickup/hdrgen_AMDRaspian.tar.gz
sudo tar -C /usr/local/bin/ -xvf  hdrgen_AMDRaspian.tar.gz
rm hdrgen_AMDRaspian.tar.gz
```

### Install evalglare
```
git clone https://github.com/NREL/Radiance.git
cd Radiance/
sudo ./makeall install
```


### Install labjack software:
```
git clone https://github.com/labjack/exodriver.git
cd exodriver
sudo ./install.sh
cd ../
sudo pip3 install labjackpython
```

