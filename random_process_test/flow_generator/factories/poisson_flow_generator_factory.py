'''
An implementation of the Abstract Generator Factory interface that
uses poisson processes in order to generate flows.
'''


from abstract_factory  import Abstract_Generator_Factory
from flow_generator.generators.poisson_flow_generator import Poisson_Flow_Generator




class Poisson_Generator_Factory(Abstract_Generator_Factory):

    def __init__(self, network_load):
        super(Poisson_Generator_Factory, self).__init__()

        if network_load <= 0.0:
            raise ValueError("Load must be positive")

        self.m_load = network_load # network load for this simulation


    def set_load(self, load):
        if load > 0.0: # only if the load is positive
            self.m_load = load


    def create_generator(self):
        load = self.m_load

        return Poisson_Flow_Generator(load)

