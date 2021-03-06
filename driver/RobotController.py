# Robot controller
#
# class ServoController
#
# class Robot
#
#

import RPi.GPIO as G
import threading
import Mission
import RobotHelper


class ServoController():

    """A class used to asynchronously control the servo motors"""

    def __init__(self, pin, state=0.5, timeRange=(1.0, 2.0)):
        self.pin = pin  # pin on which the servo lives
        self.timeRange = timeRange  # the time bounds for the servo
        self.state = state  # the percentage state
        self.servoThread = threading.Thread()
        self.servoStopEvent = threading.Event()

    def _sendSignal(self):
        wait_time = (self.timeRange[0] + self.state * (self.timeRange[1] - self.timeRange[0])) / 1000.0
        print 'wait time', wait_time
        G.output(self.pin, 1)
        self.servoStopEvent.wait(wait_time)
        G.output(self.pin, 0)

    def _checkRange(self, state):
        return state <= 1.0 and state >= 0.0

    def updateServo(self):
        print 'state', self.state
        if not self.servoThread.isAlive():
            if self._checkRange(self.state):
                # We must make the thread newly because you can't restart threads in python
                self.servoThread = threading.Thread(target=self._sendSignal)
                self.servoThread.start()

    def incr(self, value=0.05):
        state = self.state + value
        if self._checkRange(state):
            self.state = state
            self.updateServo()

    def decr(self, value=0.05):
        state = self.state - value
        if self._checkRange(state):
            self.state = state
            self.updateServo()

    def setState(self, state=0.5):
        if self._checkRange(state):
            self.state = state
            self.updateServo()


class Robot():

    """A class for interacting with the Raspberry Pi Robot"""

    def __init__(self, pins, freq=50, board=G.BOARD):

        G.setmode(board)  # initialization of GPIO ports
        G.setup(pins['RightFront'], G.OUT)
        G.setup(pins['RightBack'], G.OUT)
        G.setup(pins['LeftFront'], G.OUT)
        G.setup(pins['LeftBack'], G.OUT)

        G.setup(pins['Light'], G.OUT)
        G.setup(pins['Laser'], G.OUT)

        G.setup(pins['ServoH'], G.OUT)
        G.setup(pins['ServoV'], G.OUT)

        # set up pin refs
        self.pins = pins
        self.frequency = freq

        # keep track of the status of the components
        self.component = {
            "light": False,
            "laser": False
        }

        # the current mission in progress
        self.mission = None

        # The time range for servos
        servoRange = (0.68, 1.95)
        self.servoControlles = [
            ServoController(pins['ServoH'], 0.5, servoRange),
            ServoController(pins['ServoV'], 0.5, servoRange)
        ]

        # array of pins
        self.pinArray = {
            "RightFront": G.PWM(self.pins["RightFront"], self.frequency),
            "RightBack": G.PWM(self.pins["RightBack"], self.frequency),
            "LeftFront": G.PWM(self.pins["LeftFront"], self.frequency),
            "LeftBack": G.PWM(self.pins["LeftBack"], self.frequency)
        }

        # Thread Locks for GPIO interface
        self.pinsTL = threading.Lock()
        self.componentTL = threading.Lock()

    def go(self, speed, direction):
        """update the speed and direction of the robot"""

        rightM = 0
        leftM = 0
        if direction == 0:
            rightM = 100
            leftM = 100
        elif direction == 45:
            rightM = 50
            leftM = 100
        elif direction == -45:
            rightM = 100
            leftM = 50
        elif direction == 90:
            rightM = -80
            leftM = 80
        elif direction == -90:
            rightM = 80
            leftM = -80
        elif direction == 135:
            rightM = -50
            leftM = -100
        elif direction == -135:
            rightM = -100
            leftM = -50
        elif abs(direction) == 180:
            rightM = -100
            leftM = -100

        speed = speed / 100.0
        rightM = rightM * speed
        leftM = leftM * speed
        print rightM, leftM
        self.pinsTL.acquire()  # acquire a Thread Lock
        if RobotHelper.isPositive(rightM):
            self.pinArray["RightBack"].stop()
            self.pinArray["RightFront"].start(rightM)
        else:
            self.pinArray["RightFront"].stop()
            self.pinArray["RightBack"].start(abs(rightM))

        if RobotHelper.isPositive(leftM):
            self.pinArray["LeftBack"].stop()
            self.pinArray["LeftFront"].start(leftM)
        else:
            self.pinArray["LeftFront"].stop()
            self.pinArray["LeftBack"].start(abs(leftM))
        self.pinsTL.release()  # release the Thread Lock

    def stop(self):
        """stop the robot"""
        self.pinsTL.acquire()
        for key in self.pinArray:
            self.pinArray[key].stop()  # Stop the PWM on each output pins
        self.pinsTL.release()

    def setLight(self, state):
        """Set the light to a given state"""
        self.componentTL.acquire()
        self.component["light"] = state
        G.output(self.pins["Light"], int(state))
        self.componentTL.release()

    def getLight(self):
        """get the status of the light"""
        return self.component["light"]

    def setLaser(self, state):
        """Set the laser to a state"""
        self.componentTL.acquire()
        self.component["laser"] = state
        G.output(self.pins["Laser"], int(state))
        self.componentTL.release()

    def getLaser(self):
        """get the status of the laser"""
        return self.component["laser"]

    def startMission(self, moves):
        """start a mission"""
        if self.mission == None:
            self.mission = Mission.Mission(self, moves)
            self.mission.start()

    def stopMission(self):
        """stop a mission"""
        if self.mission:
            self.mission.stop()
            self.mission = None

    def changeCam(self, state):
        """change the cam to a new state"""

        if not state == [0, 0, 0, 0]:
            if len(state) == 4:
                if state[0]:
                    self.servoControlles[1].decr()

                if state[1]:
                    self.servoControlles[0].incr()

                if state[2]:
                    self.servoControlles[1].incr()

                if state[3]:
                    self.servoControlles[0].decr()

            else:
                self.servoControlles[0].setState(0.5)
                self.servoControlles[1].setState(0.5)

    def closeMe(self):
        """clean up"""
        G.cleanup()

if __name__ == "__main__":
    pass
