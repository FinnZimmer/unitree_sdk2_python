import math
import ctypes
import platform
import time
from .clib_lookup import CLIBLookup

class timespec(ctypes.Structure):
    _fields_ = [("sec", ctypes.c_long), ("nsec", ctypes.c_long)]
    __slots__ = [name for name,type in _fields_]

    @classmethod
    def from_seconds(cls, secs):
        c = cls()
        c.seconds = secs
        return c
    
    @property
    def seconds(self):
        return self.sec + self.nsec / 1000000000

    @seconds.setter
    def seconds(self, secs):
        x, y = math.modf(secs)
        self.sec = int(y)
        self.nsec = int(x * 1000000000)


class itimerspec(ctypes.Structure):
    _fields_ = [("interval", timespec),("value", timespec)]
    __slots__ = [name for name,type in _fields_]
    
    @classmethod
    def from_seconds(cls, interval, value):
        spec = cls()
        spec.interval.seconds = interval
        spec.value.seconds = value
        return spec

# macOS compatibility layer
if platform.system() == 'Darwin':
    class TimerFD:
        def __init__(self, clock_type, flags):
            self.interval = 0
            self.next_time = 0
            
        def settime(self, flags, new_value, old_value):
            if new_value:
                self.interval = new_value.interval.seconds
                self.next_time = time.time() + self.interval
            return 0
            
        def gettime(self, curr_value):
            if curr_value:
                curr_value.interval.seconds = self.interval
                curr_value.value.seconds = max(0, self.next_time - time.time())
            return 0
            
        def read(self, size):
            current_time = time.time()
            if current_time >= self.next_time:
                self.next_time = current_time + self.interval
                return b'\x01\x00\x00\x00\x00\x00\x00\x00'  # Return 1 in little-endian
            return b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Return 0 in little-endian
            
        def close(self):
            pass

    def timerfd_create(clock_type, flags):
        return TimerFD(clock_type, flags)
        
    def timerfd_settime(fd, flags, new_value, old_value):
        return fd.settime(flags, new_value, old_value)
        
    def timerfd_gettime(fd, curr_value):
        return fd.gettime(curr_value)
        
else:
    # Linux implementation using timerfd
    timerfd_create = CLIBLookup("timerfd_create", ctypes.c_int, (ctypes.c_long, ctypes.c_int))
    timerfd_settime = CLIBLookup("timerfd_settime", ctypes.c_int, (ctypes.c_int, ctypes.c_int, ctypes.POINTER(itimerspec), ctypes.POINTER(itimerspec)))
    timerfd_gettime = CLIBLookup("timerfd_gettime", ctypes.c_int, (ctypes.c_int, ctypes.POINTER(itimerspec)))
