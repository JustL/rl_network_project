'''
An implementation of the Abstract Generator Factory interface that
uses poisson processes in order to generate flows.
'''


from abstract_factory  import Abstract_Generator_Factory
from flow_generator.generators.poisson_flow_generator import Poisson_Flow_Generator




class Poisson_Generator_Factory(Abstract_Generator_Factory):


    __NETWORK_LOADS = [300, 500, 800] # network loads (Mbps)

    def __init__(self):
        super(Poisson_Generator_Factory, self).__init__()

        self.m_load =  -1.0 # network load for this simulation
        self.m_index = 0    # for cases when net load is not provided

    def set_load(self, load):
        if load > 0.0: # only if the load is positive
            self.m_load = load


    def create_generator(self):

        load = Poisson_Generator_Factory.__NETWORK_LOADS[0]
        if self.m_load > 0.0:
            load = self.m_load

        else:
            load = Poisson_Generator_Factory.__NETWORK_LOADS[self.m_index]
            self.m_index = (self.m_index + 1) % len(Poisson_Generator_Factory.__NETWORK_LOADS)

        return Poisson_Flow_Generator(load)

