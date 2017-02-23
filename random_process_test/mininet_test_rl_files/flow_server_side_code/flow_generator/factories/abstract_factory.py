'''
This file contains an interface that every flow generator
factory must implement in order to be used by flow processes.
In other words, this abstraction is used by processes that
generate/send flows to other remote servers.
'''



class Abstract_Generator_Factory(object):

    '''
    An abstract method for creating custom flow generators.
    '''
    def create_generator(self):
        pass

