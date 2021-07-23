import numpy as np
import imutils
import cv2
import yarp
import numpy

#########################
# OPENCV initialization #
#########################
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))
net = cv2.dnn.readNetFromCaffe("od/MobileNetSSD_deploy.prototxt.txt", "od/MobileNetSSD_deploy.caffemodel")

#######################
# YARP initialization #
#######################
yarp.Network.init()

# create a port and connect it to the iCub simulator virtual camera
input_port = yarp.Port()
input_port.open("/python-image-port")
yarp.Network.connect("/icubSim/cam/right/rgbImage:o", "/python-image-port")

# create numpy array to receive the image and the YARP image wrapped around it
img_array = numpy.zeros((240, 320, 3), dtype=numpy.uint8)
yarp_image = yarp.ImageRgb()
yarp_image.resize(320, 240)
yarp_image.setExternal(img_array, img_array.shape[1], img_array.shape[0])

# connect for arm control
props = yarp.Property()
props.put("device", "remote_controlboard")
props.put("local", "/client/right_arm")
props.put("remote", "/icubSim/right_arm")
rightArmDriver = yarp.PolyDriver(props)
riPos = rightArmDriver.viewIPositionControl()
riVel = rightArmDriver.viewIVelocityControl()
riEnc = rightArmDriver.viewIEncoders()

# retrieve number of joints
jnts = riPos.getAxes()
print('left: Controlling', jnts, 'joints')

# increase joint speed
sp = 100

riPos.setRefSpeed(0, sp)
riPos.setRefSpeed(1, sp)
riPos.setRefSpeed(3, sp)
usent = False
dsent = False

#############
# main loop #
#############
while True:
    saw = False

    # get image
    input_port.read(yarp_image)
    frame = imutils.resize(img_array, width=400)
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    # loop over the detections
    for i in np.arange(0, detections.shape[2]):

        # extract the probabilities
        confidence = detections[0, 0, i, 2]

        if confidence > 0.5:
            # extract the index of the class label from the
            # `detections`, then compute the (x, y)-coordinates of
            # the bounding box for the object
            idx = int(detections[0, 0, i, 1])
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            # draw the prediction on the frame
            label = "{}: {:.2f}%".format(CLASSES[idx],
                                         confidence * 100)

            if CLASSES[idx] == "person":
                saw = True

            cv2.rectangle(frame, (startX, startY), (endX, endY),
                          COLORS[idx], 2)
            y = startY - 15 if startY - 15 > 15 else startY + 15
            cv2.putText(frame, label, (startX, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)

    # if iCub saw a person, he raises the right arm
    if saw and not usent:
        riPos.positionMove(1, 90)
        riPos.positionMove(0, -90)
        riPos.positionMove(3, 100)

        usent = True
        dsent = False

    # otherwise, come back in original position
    if not saw and not dsent:
        riPos.positionMove(0, -30)
        riPos.positionMove(1, 30)
        riPos.positionMove(3, 45)

        dsent = True
        usent = False

    # show the output frame
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

# do a bit of cleanup
cv2.destroyAllWindows()
input_port.close()

