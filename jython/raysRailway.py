import jmri
import java
import jarray
import java.beans
import httplib
import socket
from org.apache.log4j import *

from com.pi4j import Pi4J
from com.pi4j.io.gpio.digital import DigitalOutput, DigitalOutputProvider, DigitalState, DigitalStateChangeListener

pi4j = Pi4J.newAutoContext()
# Find the MqttAdapter
mqttAdapter = jmri.InstanceManager.getDefault(jmri.jmrix.mqtt.MqttSystemConnectionMemo).getMqttAdapter()


class MyListener(java.beans.PropertyChangeListener):
    log = Logger.getLogger("jmri.jmrit.jython.exec.RaysRailway.MyListener")

    def propertyChange(self, event):

        self.log.info("systemName: " + event.source.systemName)
        self.log.info("change: " + event.propertyName)
        self.log.info("from: " + str(event.oldValue) + " to: " + str(event.newValue))

        if event.propertyName == "KnownState":

            k = 1
            # Check sensors 33-49 (left button block). Increment by 2, because each turnout has two output bits
            # So we have CT1, CT3, CT5 etc
            # for i in range(33, 49):
            for i in range(33, 41):
                if event.source.systemName == "CS" + str(i) and event.newValue == ACTIVE and event.oldValue != ACTIVE:
                    self.log.info("Button " + str(i - 32) + " pressed")
                    if turnouts.getTurnout("CT" + str(k)).getState() == CLOSED:
                        self.log.info("Setting turnout " + str(k) + " state to THROWN")
                        turnouts.getTurnout("CT" + str(k)).setState(THROWN)
                    else:
                        self.log.info("Setting turnout " + str(k) + " state to CLOSED")
                        turnouts.getTurnout("CT" + str(k)).setState(CLOSED)
                k += 2

            k = 1
            for i in range(41, 49):
                if event.source.systemName == "CS" + str(i) and event.newValue == ACTIVE and event.oldValue != ACTIVE:
                    self.log.info("Button " + str(i - 32) + " pressed")
                    if turnouts.getTurnout("MT" + str(k)).getState() == CLOSED:
                        self.log.info("Setting MQTT turnout " + str(k) + " state to THROWN")
                        turnouts.getTurnout("MT" + str(k)).setState(THROWN)
                    else:
                        self.log.info("Setting MQTT turnout " + str(k) + " state to CLOSED")
                        turnouts.getTurnout("MT" + str(k)).setState(CLOSED)
                k += 1


            # Right hand key block -> maps to single-bit turnouts (we could make these lights really) 65 -
            #k = 65
            k = 17
            for i in range(49, 65):
                if event.source.systemName == "CS" + str(i) and event.newValue == ACTIVE and event.oldValue != ACTIVE:
                    self.log.info("Button " + str(i - 32) + " pressed")
                    if turnouts.getTurnout("CT" + str(k)).getState() == CLOSED:
                        self.log.info("Setting turnout " + str(k) + " state to THROWN")
                        turnouts.getTurnout("CT" + str(k)).setState(THROWN)
                    else:
                        self.log.info("Setting turnout " + str(k) + " state to CLOSED")
                        turnouts.getTurnout("CT" + str(k)).setState(CLOSED)
                k += 1

            # Bottom key block (sounds). Here we can just send custom MQTT messages
            for i in range(65, 73):
                if event.source.systemName == "CS" + str(i) and event.newValue == ACTIVE and event.oldValue != ACTIVE:
                    topic = "audio/" + str(i - 64)
                    payload = "PLAY"
                    # send MQTT message
                    mqttAdapter.publish(topic, payload)

            # feedback from turnouts back to button LEDs
            for i in range(1, 17, 2):
                if event.source.systemName == "CT" + str(i):
                    self.log.info("External output " + str(i) + " state changed. Setting corresponding LED state")
                    turnouts.getTurnout("CT" + str(i + 32)).setState(event.newValue)

            for i in range(17, 33):
                if event.source.systemName == "CT" + str(i):
                    self.log.info("External output " + str(i) + " state changed. Setting corresponding LED state")
                    turnouts.getTurnout("CT" + str(i + 48)).setState(event.newValue)

            k = 49
            for i in range(1, 9):
                if event.source.systemName == "MT" + str(i):
                    self.log.info("MQTT turnout " + str(i) + " state changed. Setting corresponding LED state")
                    turnouts.getTurnout("CT" + str(k)).setState(event.newValue) # 32 buttons begin, + 16 second half of block
                k += 2

        return


listener = MyListener()


# Define the shutdown task
class MyShutDownTask(jmri.implementation.AbstractShutDownTask):
    log = Logger.getLogger("jmri.jmrit.jython.exec.RaysRailway.MyShutdownTask")

    def run(self):
        pi4j.shutdown()

        # For the sensors that exist, attach a sensor listener
        sensorList = sensors.getNamedBeanSet()
        for sensor in sensorList:
            sensor.removePropertyChangeListener(listener)

        self.log.info("Shutting down turnouts")
        turnoutList = turnouts.getNamedBeanSet()
        for turnout in turnoutList:
            turnout.setState(UNKNOWN)
            turnout.removePropertyChangeListener(listener)


        self.log.info("Swotcjomg pff track power")
        powermanager.setPower(jmri.PowerManager.OFF)

        return


shutdown.register(MyShutDownTask("RaysRailway"))


class RaysRailway(jmri.jmrit.automat.AbstractAutomaton):
    log = Logger.getLogger("jmri.jmrit.jython.exec.RaysRailway.RaysRailway")

    def init(self):

        self.log.info("Initialising front panel")

        self.log.info("Configuring external inputs as sensors")

        for i in range(1, 33):
            s = sensors.provideSensor("CS" + str(i))
            s.setUserName("EXT_IN_" + str(i))
            s.setComment("External input " + str(i))

        self.log.info("Configuring front panel buttons as sensors")

        for i in range(33, 73):
            s = sensors.provideSensor("CS" + str(i))
            s.setUserName("BTN_" + str(i - 32))
            s.setComment("Keypad button " + str(i - 32))

        self.log.info("Configuring external outputs as turnouts")

        for i in range(1, 17, 2):
            t = turnouts.provideTurnout("CT" + str(i))
            t.setUserName("EXT_OUT_" + str(i) + "_" + str(i + 1))
            t.setComment("External output " + str(i))
            t.setNumberControlBits(2)
            t.setState(CLOSED)

        for i in range(17, 33):
            t = turnouts.provideTurnout("CT" + str(i))
            t.setUserName("EXT_OUT_" + str(i))
            t.setComment("External output " + str(i))
            t.setNumberControlBits(1)
            t.setState(CLOSED)

        self.log.info("Configuring button LEDs as turnouts")

        for i in range(33, 65, 2):
            t = turnouts.provideTurnout("CT" + str(i))
            t.setUserName("BTN_LED_" + str(i - 32) + "_" + str(i - 31))
            t.setComment("Button LEDs " + str(i - 32) + " and " + str(i - 31))
            t.setNumberControlBits(2)
            t.setState(CLOSED)

        for i in range(65, 81):
            t = turnouts.provideTurnout("CT" + str(i))
            t.setUserName("BTN_LED_" + str(i - 32))
            t.setComment("Button LED " + str(i - 32))
            t.setNumberControlBits(1)
            t.setState(CLOSED)

        for i in range(1, 25):
            t = turnouts.provideTurnout("MT" + str(i))
            t.setUserName("REMOTE_TURNOUT_" + str(i))
            t.setComment("Remote turnout " + str(i))
            t.setNumberControlBits(2)
            t.setState(CLOSED)

        for i in range(1, 17):
            l = lights.provideLight("ML" + str(i))
            l.setUserName("REMOTE_LIGHT_" + str(i))
            l.setComment("Remote light " + str(i))
            l.setState(OFF)

        # For the sensors that exist, attach a sensor listener
        sensorList = sensors.getNamedBeanSet()
        for sensor in sensorList:
            sensor.addPropertyChangeListener(listener)

        turnoutList = turnouts.getNamedBeanSet()
        for turnout in turnoutList:
            turnout.addPropertyChangeListener(listener)

        lightList = lights.getNamedBeanSet()
        for light in lightList:
            turnout.addPropertyChangeListener(listener)

        try:
            # create a digital input instance using the default digital input provider
            # we will use the PULL_DOWN argument to set the pin pull-down resistance on this GPIO pin

            # get a Digital Input I/O provider from the Pi4J context
            output = pi4j.dout().create(18)
            output.config().shutdownState(DigitalState.LOW)

            # Set ready LED to on
            output.high()

            powermanager.setPower(jmri.PowerManager.ON)
        except java.lang.reflect.UndeclaredThrowableException:
            self.log.info("error")

        return

    def handle(self):

        #	if self.hasDaylightSensor == True:
        #		try:
        #			self.log.info("Reading daylight sensor value")
        #			conn2 = httplib.HTTPConnection("rr_daylightmodule_1.local",80,30)
        #			conn2.request("GET", "/value")
        #			response = conn2.getresponse()
        #			lux = float(response.read())
        #			if lux < 50:
        #				self.log.info("Threshold reached. Daylight sensor activated")
        #				turnouts.getTurnout("CT34").setState(THROWN)
        #
        #		except (socket.error, httplib.HTTPException):
        #			self.log.info("An error occurred reading from daylight module")
        #		finally:
        #			if conn2:
        #				conn2.close()

        return True


# end of class definition


# Create one of these
rr = RaysRailway()

rr.setName("Ray's Railway")

# Start one of these up
rr.start()

