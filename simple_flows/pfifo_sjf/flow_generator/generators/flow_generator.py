'''
An interface that is used by processes that generate flows in order
to generate flow sizes and timing. The interface provide the most
important methods for generating flows.



Adapted from Wei Bai traffic generator.
'''

import sys


RAND_MAX = sys.maxint

# defaut goodput / link capacity ratio
TG_GOODPUT_RATIO = (1448.0 / (1500 + 14 +4 + 8 + 12))


class Flow_Generator(object):

    '''
    Load cdf from  a file.
    '''
    def load_cdf(self, filename):
        pass


    '''
    Print a random process distribution.
    '''
    def print_cdf(self):
        pass


    '''
    Calculate the average of the random process
    underlying distribution.
    '''
    def avg_cdf(self):
        return 0.0


    '''
    Key function that returns size a random
    value based on a CDF distribution.
    '''
    def gen_random_cdf(self):
        return 0.0


    '''
    Interface for different generators
    to determine interval between sending
    a new flow.

    Args:
        params : an arbitrary dictionary that stores values
                 particualr for some distribution/process.
    '''
    def gen_random_interval(self, **params):
        0.0
