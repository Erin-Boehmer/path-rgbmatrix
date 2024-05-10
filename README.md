# NJPath RGBMatrix Display

Circuitpython code to display PATH train arrivals at Grove Street in Jersey City.

<img src="./media/demo.jpg?raw=true" width="300">

## Materials
* [1 x 64x32 RGB LED Matrix - 3mm pitch](https://www.adafruit.com/product/2279) (can use any pitch)
* [1 x Adafruit Matrix Portal S3 CircuitPython Powered Internet Display](https://www.adafruit.com/product/5778)
* usb-c data cable

## Configuration
* S3 matrix portal setup
    * I had to do a factory reset of my microcontroller because it wasn't shipped with the bootloader. Instructions for reset [here](https://learn.adafruit.com/adafruit-matrixportal-s3/factory-reset#factory-reset-and-bootloader-repair-3107941).
    * Installed circuit python (steps [here](https://learn.adafruit.com/rgb-matix-nyt-text-scroller/install-circuitpython)) and required libraries (bundle [here](https://circuitpython.org/libraries)). 
* If you did not use a 64x32 RBGMatrix size, you'll need to update the RGBMatrix setup in `code.py`
* I'm configuring for NYC bound trains arriving at Grove Street in Jersey City. You can configure the APIs to use a different station by updating `api/shared_config.py`
