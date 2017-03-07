'''
File contains an implementation of a Poisson Process that is
used for generating flow sizes.
'''


import random
import math

from flow_generator import Flow_Generator
from flow_generator import RAND_MAX
from flow_generator import TG_GOODPUT_RATIO



'''
A simple class that represents an item
in a cdf (for refer to Wei Bai's C implementation
available on github)
'''
class  CDF_Entry(object):

    def __init__(self, value=0.0, cdf=0.0):
        self.m_value = value
        self.m_cdf   = cdf



class Poisson_Flow_Generator(Flow_Generator):

    '''
    Almost direct mapping from Wei Bai's C implementation.
    '''
    def __init__(self, network_load):
        super(Poisson_Flow_Generator, self).__init__()

        self.m_table = []
        self.m_max_cdf = 1.0
        self.m_min_cdf = 0.0
        self.m_load    = network_load if network_load > 0.0 else 1.0
        self.m_avg     = -1.0



    '''
    Load a traffic distribution from a
    file.
    '''
    def load_cdf(self, filename):

        # open the given file and
        # read data from it.


        with open(name=filename, mode="r") as fd:
            while 1:
                line = fd.readline() # read a line

                if line == None or line == "":
                    break

                line = line[0:-1:1]    # discard '\n'
                vals = line.split(None)


                if len(vals) % 2 != 0:
                    raise ValueError(
                        "Input file has invalid input structure.")

                for idx in xrange(0,len(vals),2):
                    # read two values a a time (value, cdf)
                    value = float(vals[idx])
                    cdf   = float(vals[idx + 1])


                    self.m_table.append(CDF_Entry(
                        value, cdf))

                    # update some default values from the read values
                    if cdf < self.m_min_cdf:
                        self.m_min_cdf = cdf

                    if cdf > self.m_max_cdf:
                        self.m_max_cdf = cdf


    '''
    Print the CDF hold by this object.
    '''
    def print_cdf(self):

        for entry in self.m_table:
            print "%.2f %.2f\n" % (entry.m_value, entry.m_cdf)



    '''
    Compute and return the average of the
    underlying Poisson distribution.
    '''
    def avg_cdf(self):

        if not self.m_table: # return zero
            return 0.0


        avg = 0.0

        avg += (self.m_table[0].m_value / 2) * self.m_table[0].m_cdf

        # loop though all table entries and
        # return compute avg (taken from Wi Bai's code)
        for idx in xrange(1, len(self.m_table), 1):
            value = (self.m_table[idx].m_value
                    + self.m_table[idx-1].m_value)/2

            prob = self.m_table[idx].m_cdf - self.m_table[idx-1].m_cdf

            avg += (value * prob)


        return avg # return computed value


    '''
    Helper function for generating a random value
    from the underlying distribution.
    '''
    def _interpolate(self, x, x1, y1, x2, y2):

        if x1 == x2:
            return (y1 + y2) / 2

        return y1 + (x - x1) * (y2 - y1) / (x2 - x1)



    '''
    Helper function for generating a rnadom vlaue based on the
    underlying CDF distribution.
    '''
    def _rand_range(self, min_cdf, max_cdf):
        return (min_cdf
                + random.randint(0, RAND_MAX)
                * (max_cdf - min_cdf) / RAND_MAX)


    '''
    Generates a random value based on CDF distribution.
    '''
    def gen_random_cdf(self):

        # if the table is empty,
        # return zero
        if not self.m_table:
            return 0.0


        x = self._rand_range(self.m_min_cdf, self.m_max_cdf)

        # check for the first item
        if x <= self.m_table[0].m_cdf:
            return self._interpolate(x, 0, 0,
                    self.m_table[0].m_cdf,
                    self.m_table[0].m_value)


        for idx in xrange(1, len(self.m_table), 1):

            if x <= self.m_table[idx].m_cdf:
                return self._interpolate(x,
                        self.m_table[idx-1].m_cdf,
                        self.m_table[idx-1].m_value,
                        self.m_table[idx].m_cdf,
                        self.m_table[idx].m_value)

        # by default, return the last value
        return self.m_table[-1].m_value


    '''
    Generates a Poisson random process interval for
    sleeping. In other words, returns time to sleep
    for a particular flow -- interval between the end
    of one session of the flow and the begginning of
    a new session of the flow -- in microseconds.

    Args:
        **params : must contain avg_rate key and value

    return : Poisson random process interval in us.
    '''
    def gen_random_interval(self, **params):

        if self.m_avg < 0.0:
            period_us = self.avg_cdf() * 8 / self.m_load / TG_GOODPUT_RATIO

            if period_us <= 0.0:
                raise RuntimeError("Poisson distribution generated a negative period_us")

            self.m_avg = 1.0 / period_us
            self.m_avg = self.m_avg if self.m_avg != 0.0 else 0.005

        lmb = self.m_avg

        val = 1.0 - (random.randint(0, RAND_MAX-1) / float(RAND_MAX))

        return  ( -math.log(val, math.e) / lmb )


