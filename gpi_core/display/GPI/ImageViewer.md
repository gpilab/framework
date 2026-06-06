# Image Viewer
Creates an Image Viewer widget that accepts a numpy array and converts into a RGBA image for display & manipulation
![Screen Shot 2021-11-01 at 4 42 10 PM](https://user-images.githubusercontent.com/12875975/139745950-8c937319-1982-4c59-9d89-a8b13312434b.png)

## Table of Contents
1. [Prerequisites](#Prerequisites)
2. [Controls](#Controls)
    1. [Resizing Viewer](#Resizing-Viewer)
    2. [Scrolling through slices](#Scrolling-through-slices)
    3. [Window Leveling](#Window-Leveling)
3. [Color Map](#Color-Map)
4. [ROIS](#ROIS)
    1. [Create ROI](#Create-ROI)
    2. [Remove ROI](#Remove-ROI)
    3. [Propogate ROI](#Propogate-ROI)
    4. [Mask ROI](#Mask-ROI)
    5. [Copy & Paste ROI](#Copy--Paste-ROI)
    6. [Free Hand ROI](#Free-Hand-ROI)
    7. [Modify ROIS Shape](#Modify-ROIS-Shape)
5. [Menus](#Menus)
    1. [Image Menu](#Image-Menu)
    2. [Window Leveling Menu](#Window-Leveling-Menu)
    3. [Color Map Menu](#Color-Map-Menu)
    4. [ROI Menu](#ROI-Menu)
6. [Shortcuts](#Shortcuts)
    1. [ROI Shortcuts](#ROI-Shortcuts)
7. [Issues & Improvements](#Issues--Improvements)


### Prerequisites

You will need `pyqtgraph` installed in you GPI environment.

1. Activate your GPI environment
```
conda activate 'YOUR GPI ENV'
```
2. Install `pyqtgraph`
```
conda install pyqtgraph
```

## Controls

### Resizing Viewer
<kbd>cmd</kbd> / <kbd>ctrl</kbd> + Mouse Drag

![ezgif com-gif-maker (1)](https://user-images.githubusercontent.com/12875975/139782815-91aa5f67-e1b4-49ef-9951-98a98ef15927.gif)

### Scrolling through slices
<kbd>shift</kbd> + Mouse Wheel/Mouse Scroll

![ezgif com-gif-maker (3)](https://user-images.githubusercontent.com/12875975/139783450-5f3b3a57-0d2a-4686-b4fd-59329aa019a5.gif)

### Window Leveling
<kbd>shift</kbd> + Mouse Move
* Left & Right: Changes window
* Up & Down: Changes Level

Note: The min and max of the window represent range min adn max. Fix Range is on when you start window leveling

![ezgif com-gif-maker (5)](https://user-images.githubusercontent.com/12875975/139873173-08592b4f-901f-4e1b-9dc6-7d6fd4939467.gif)

## Color Map
You can color map your image by right-clicking on the color bar on the righ hand side. You can choose a preset color map or create your own by double-clicking on the color bars to add new color ranges.

Note: Color maps wont apply on complex data or sign images.

![ezgif com-gif-maker (6)](https://user-images.githubusercontent.com/12875975/139874564-324d274f-6727-4a07-8d53-65acde53f62c.gif)

## ROIS

### Create ROI
You can create an ROI by clicking on of the buttons on top of the image viewer or use one of the shortcuts, then left-clicking on the position you want your ROI to be placed.

![ezgif com-gif-maker (8)](https://user-images.githubusercontent.com/12875975/139876777-b9d17d8c-844c-4c5f-b46b-56d7d91ca09f.gif)

### Remove ROI
Right-click on the ROI you want to remove to show the ROI menu then choose remove ROI.

![ezgif com-gif-maker (9)](https://user-images.githubusercontent.com/12875975/139877000-8bf8a3d7-266b-4111-8239-8bc8fdcf6cad.gif)

### Propogate ROI
Right-click on the ROI you want to remove to show the ROI menu then choose remove ROI. This will make the ROI propogate through all the slices.

![ezgif com-gif-maker (11)](https://user-images.githubusercontent.com/12875975/139880366-6c59b86b-a5ea-4355-8366-82ce68ca4840.gif)

### Mask ROI
You have 3 options to mask an image in two different ways, you can mask the image either using one ROI or all ROIS.
* Image: masks the RGBA image and sets the output port to it
* Binary: Creates a 0-1 mask of the ROI region and sets the binary output port to it
* 1D: Creates a 1D numpy array of the concatenated ROI regions of the actual data used to generate the RGBA and sets the 1D output port to it

To mask on one ROI: Right-click on the ROI to show the ROI menu and choose the masking option 
To mask on all ROIs: Right-click on the image to show the image menu and choose the masking option 

![ezgif com-gif-maker (10)](https://user-images.githubusercontent.com/12875975/139879038-ef78034f-a5c7-4811-a34d-a2eb8ab4b2ef.gif)

### Copy & Paste ROI
Right-click on the ROI you want to copy to show the ROI menu then choose copy ROI. Then right-click on the image at the position you want to paste the ROI to show the image menu then choose paste.

Note: Only `Free Hand` & `Closed Polygon` ROIs can be copied at the moment.

![ezgif com-gif-maker (12)](https://user-images.githubusercontent.com/12875975/139881097-75e57e88-e180-4eea-9c63-cf794b495305.gif)

### Free Hand ROI
To create a free hand ROI select its button on top of the image viewer or use its shortcut, then do a one left-click on the image at the position you want to start to create the first point and draw by moving your mouse, when done do a left-click to close the ROI. 

![ezgif com-gif-maker (13)](https://user-images.githubusercontent.com/12875975/139886380-b59b8b1e-b58e-4705-8563-6c9bc775cf32.gif)

### Modify ROIS Shape
You can modify the shape of `Free Hand` & `Closed Polygon` ROIs by double clicking on their lines to add new handles and right-click on their handles to remove them.

![ezgif com-gif-maker (14)](https://user-images.githubusercontent.com/12875975/139888992-74687767-4814-4e0c-93f5-69947bf2874c.gif)

## Menus

### Image Menu
Right-click on the image view to show the image menu which includes the following options.
* Copy: copies the image to clipboard
* Paste: pastes a copied ROI
* Interpolate: does a bicubic interpolation on the image
* Mask: masks all ROIs
* Flip X: flips the x-axis of the image
* Flip Y: flips the y-axis of the image
* Recenter: recenter the view to have the image in the center of the view
* Reset: resets the image to its original form before any masking
* Export: gives you save, copy options to export the image view

### Window Leveling Menu
Right-click on the window level bar to show the window level menu which includes the following options.
* Fix Range: fixes the range min and max
* Set Range: use it to set the range min and max (Enabled when Fix Range is on)
* Set Gamma: use it to set Gamma
* Set Zero Ref: use it to Zero Ref
* Reset: resets the range min and max to the slice range min and max that was used to Fix Range

### Color Map Menu
Right-click on the color map bar to show the color map menu which includes the following options.
* Presets of color maps
* RGB: RGB mode
* HSV: HSV (hue, saturation, value) mode

### ROI Menu
Right-click on a ROI to show the ROI menu which includes the following options.
* Remove ROI
* Copy ROI
* Propogate ROI
* Mask ROI

## Shortcuts

### ROI Shortcuts

<kbd> M </kbd> : Mouse

<kbd> P </kbd> : Point ROI

<kbd> L </kbd> : Line ROI

<kbd> R </kbd> : Rectangle ROI

<kbd> E </kbd> : Ellipse ROI

<kbd> C </kbd> : Closed Polygon ROI

<kbd> F </kbd> : Free Hand ROI

Note: Both uppercase and lowercase letters will work



## Issues & Improvements

To report an issue or an improvement please create a [new issue](https://github.com/gpilab/core-nodes/issues/new) with the appropriate tag in addition to the `Image Viewer` tag.

Please be as detailed as possible. If it is a certain behaviour based on a specific network, please share it with me by email 🙂.
