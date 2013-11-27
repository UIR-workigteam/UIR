from NodesLibrary import *
from OwnMath import *
import random
from math import log
from pybrain.tools.shortcuts import buildNetwork
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import RPropMinusTrainer
from multiprocessing import Process, Queue
import copy
import xml.etree.ElementTree as ElementTree

def main_async_method(queue, xml, a):
    forest = OneForest(xml=xml)
    forest.execute()
    forest.act_neuro()
    queue.put({'fitness': forest.fitness, 'place': a})
    print '| | |-finished ', queue.qsize(),  ' forest. fitness =', forest.fitness


class OwnNeuro():
    def __init__(self, input_power, output_power, education_power):
        """
        Creating network base on input parameters: count of inputs, count of outputs and
        count of data tuple in training set.
        Count of neurons in hidden layer calculated by formula, extracted from
        Arnold - Kolmogorov - Hecht-Nielsen theorem in minimalistic form.
        """
        self.input_power = input_power
        self.output_power = output_power
        self.education_power = education_power
        self.training_errors = []
        self.validation_errors = []
        self.data_set = SupervisedDataSet(self.input_power, self.output_power)
        self.hidden_power = int(
            (output_power * education_power / (1 + log(education_power, 2))) / (input_power + output_power))
        self.network = buildNetwork(self.input_power, self.hidden_power, self.output_power)

    def _form_set(self, input_row, output_row):
        """
        Method for creating proper training set from given data.
        """
        for one_portion in range(self.education_power):
            input_tuple = ()
            for one_input in range(self.input_power):
                input_tuple += (input_row[one_input][one_portion],)
            output_tuple = ()
            for one_output in range(self.output_power):
                output_tuple += (output_row[one_output]['data'][one_portion],)
            self.data_set.addSample(input_tuple, output_tuple)

    def educate(self, input_row, output_row):
        """
        Training network by r-prop.
        PARTITION_OF_EDUCATION_VERIFICATION_SET - education|validation ratio
        MAX_EPOCHS - count of max steps of education
        OUTCASTING_EPOCHS - if education can't get out of local minimum it given count of steps, it stops
        """
        self._form_set(input_row, output_row)
        trainer = RPropMinusTrainer(module=self.network, dataset=self.data_set)
        self.training_errors, self.validation_errors = trainer.trainUntilConvergence(
            validationProportion=PARTITION_OF_EDUCATION_VERIFICATION_SET,
            maxEpochs=MAX_EPOCHS,
            continueEpochs=OUTCASTING_EPOCHS)

    def validate(self):
        return 1 / (1 + sum(self.validation_errors) / len(self.validation_errors))


class OneTree():
    """Class of one tree in modification forest trees
    """

    def _generate(self, input_element):
        """
        Generating one tree. Getting one input element as root.
        Creating chain of random functions.
        """
        nodes = sampler(LIST_OF_FUNCTIONS, random.randint(1, len(LIST_OF_FUNCTIONS)))
        self._nodes = []
        for node in nodes:
            self._nodes.append(eval(node)())
        self._inputElement = input_element

    def __init__(self, input_element=None, xml=None):
        self._nodes = []
        self._inputElement = 0
        if input_element:
            self._generate(input_element)
        elif xml:
            self._from_portal(xml)
        else:
            raise Exception('wrong arg"s')

    def execute(self):
        """
        Chain calculate results of every function in tree, starting from root value.
        """
        preput = self._inputElement['data']
        for node in self._nodes:
            preput = node.eval_me(preput)
        return preput

    def mutate(self, input_raw):
        """
        With some little probability mutate whole tree - regenerate it.
        Other way is try to mutate every node. Mutating node is just regenerating it.
        """
        random.seed()
        if random.random() < TREE_FULL_MUTATION_PROBABILITY:
            self._generate(input_raw[random.randint(0, len(input_raw)-1)])
        else:
            for nodenumber in range(len(self._nodes)):
                if random.random() < NODE_FULL_MUTATION_PROBABILITY:
                    self._nodes[nodenumber] = eval(LIST_OF_FUNCTIONS[random.randint(0, len(LIST_OF_FUNCTIONS) - 1)])()

    def store_xml(self):
        current_tree = '<tree input="' + str(self._inputElement['name']) + '" power="' + str(len(self._nodes)) + '">\n'
        for node in self._nodes:
            current_tree += node.store_xml()
        current_tree += '</tree>\n'
        return current_tree

    def _from_portal(self, xml):
        self._inputElement = xml['input']
        for noder in xml['nodes']:
            self._nodes.append(eval(noder['name'])())
            self._nodes[-1].params = noder['params']

    def to_portal(self):
        noder = []
        for node in self._nodes:
            noder.append({'name': node.__class__.__name__, 'params': node.params})
        return {'input': self._inputElement, 'nodes': noder}


class OneForest():
    def __init__(self, input_row=None, full_output=None, first_forest=None, second_forest=None, xml=None):
        """
        If we get as input two rows - we starting to generating forest.
        Another way is getting to forests - gaining new forest by crossover this two.
        """
        self._trees = []
        self.result_row = []
        self.power = None
        self._neuro = None
        self.full_output = []
        self.fitness = 0
        if input_row and full_output:
            self._generate(list(input_row), list(full_output))
        elif first_forest and second_forest:
            self._crossover(first_forest, second_forest)
        elif xml:
            self._from_portal(xml)
        else:
            raise Exception('wrong arg"s')

    def _generate(self, input_row, full_output):
        """
        Getting sublist of input row, and starting to generate new trees.
        Creating own network.
        """
        own_row = sampler(input_row, random.randint(1, 2))
        self.full_output = full_output
        self.power = len(own_row)
        self.result_row = []
        self._neuro = OwnNeuro(self.power, len(self.full_output), len(self.full_output[0]['data']))
        self.fitness = 0
        for top in own_row:
            self._trees.append(OneTree(input_element=top))

    def _crossover(self, first_forest, second_forest):
        """
        Crossing over two forests.
        Count of trees in new forest - between two previous forests.
        Getting random count of trees from first forest - others from another.
        """
        pair_power = [first_forest.power, second_forest.power]
        self.power = random.randint(min(pair_power), max(pair_power))
        print '| |-crossover power =', self.power
        count_first = random.randint(0, self.power)
        first_half_forest = first_forest.get_trees(count_first)
        second_half_forest = second_forest.get_trees(self.power - count_first)
        for tree in first_half_forest:
            self._trees.append(OneTree(xml=tree.to_portal()))
            print '>>>>>>>', tree._nodes
        for tree in second_half_forest:
            self._trees.append(OneTree(xml=tree.to_portal()))
            print '>>>>>>>', tree._nodes
        self.full_output = first_forest.full_output
        self._neuro = OwnNeuro(self.power, len(self.full_output), len(self.full_output[0]['data']))

    def get_trees(self, count):
        """
        Sampling count of random trees.
        """
        return sampler(self._trees, count)

    def execute(self):
        """
        Activating evaluation of every tree in forest
        """
        self.result_row = []

        for tree in self._trees:
            self.result_row.append(tree.execute())

    def act_neuro(self):
        """activating neuro education
        """
        self._neuro.educate(self.result_row, self.full_output)
        self.fitness = self._neuro.validate()

    def mutate(self, full_input):
        """
        With some little probability fully mutate (regenerating full forest)
        Another way try to mutate every tree in forest.
        """
        random.seed()
        if random.random() < FOREST_FULL_MUTATION_PROBABILITY:
            self._generate(full_input, self.full_output)
        else:
            for tree in self._trees:
                tree.mutate(full_input)

    def store_xml(self):
        forest_xml = ''
        for tree in self._trees:
            forest_xml += tree.store_xml()
        return forest_xml

    def async_execut_educate(self, queue):
        self.execute()
        self.act_neuro()
        queue.put(copy.deepcopy(self))
        return True

    def _from_portal(self, xml):
        self.full_output = xml['out']
        self.power = len(xml['trees'])
        self._neuro = OwnNeuro(self.power, len(self.full_output), len(self.full_output[0]['data']))
        for iteration in xml['trees']:
            self._trees.append(OneTree(xml=iteration))

    def to_portal(self):
        trees=[]
        for tree in self._trees:
            trees.append(tree.to_portal())
        return {'out': self.full_output, 'trees': trees}





class ForestCollection():
    def __init__(self, input_row=None, output_row=None, previous_generation=None):
        """
        If passed two rows - start generating collection of forests.
        Other way, if passed previous generation of collection - spawning next generation
        """
        self._fullInput = []
        self.power = 0
        self._forests = []
        self._fullOutput = []
        self.best_fitness = 0
        self.probability_gist = []
        if input_row and output_row:
            self._generate(list(input_row), list(output_row))
        elif previous_generation:
            self._next_generation(previous_generation)
        else:
            raise Exception('wrong arg"s')

    def _generate(self, input_row, output_row):
        """
        Generating number of forests (it's random in some frame).
        """
        self._fullInput = input_row
        self.power = random.randint(MIN_FORESTS_IN_COLLECTION, MAX_FORESTS_IN_COLLECTION)
        self._fullOutput = output_row
        for one_forest in range(self.power):
            self._forests.append(OneForest(input_row=input_row, full_output=self._fullOutput))

    def _next_generation(self, previous_generation):
        """
        Spawning next generation of collection by selecting n pairs of distinct forests from previous generation
        and them over.
        """
        self._fullInput, self._fullOutput = previous_generation.get_data()
        self.power = previous_generation.power
        for forest_iteration in range(self.power):
            first, second = previous_generation.selection()
            self._forests.append(OneForest(first_forest=first, second_forest=second))

    def get_data(self):
        """
        Just outputting private data.
        """
        return self._fullInput, self._fullOutput

    def execute(self):
        """
        Executing every forest in collection, activating their networks.
        By the way collecting data about best fitness function.
        """
        process_list = []
        forests_queue = Queue(self.power)
        iterational = 0
        print '| |-starting evaluation, education and validation'
        for one_forest in self._forests:
            process_list.append(Process(target=main_async_method, args=(forests_queue, copy.copy(one_forest.to_portal()), iterational)))
            iterational += 1
        for proc in process_list:
            proc.start()
        for proc in process_list:
            proc.join()
        for iter in range(forests_queue.qsize()):
            tmp = forests_queue.get()
            self._forests[tmp['place']].fitness = tmp['fitness']
        print '| |-finished'
        fitness_summ = 0
        for one_forest in self._forests:
            fitness_summ += one_forest.fitness
        self.probability_gist = []
        temp_probability = 0
        for one_forest in self._forests:
            self.probability_gist.append(temp_probability + one_forest.fitness / fitness_summ)
            temp_probability = self.probability_gist[-1]
        print '| |-', self.probability_gist

    def selection(self):
        """
        Selecting distinct pair of forests for crossover.
        Probability of selecting one forest is as much as that fitness function is better.
        """

        def select_by_prob(probability_gist):
            """selecting one point in probability gist
            """
            a = random.random()
            step = 0
            while (step < len(probability_gist)) and (probability_gist[step] < a):
                step += 1
            return step - 1
        first = select_by_prob(self.probability_gist)
        second = first
        while second == first:
            second = select_by_prob(self.probability_gist)
        print '| | |-', first,  second
        return self._forests[first], self._forests[second]

    def mutate(self):
        """
        Just mutating every forest in collection.
        """
        for forest in self._forests:
            forest.mutate(self._fullInput)

    def store_xml(self):
        forests_xml = ''
        for forest in self._forests:
            forests_xml += '<forest power="' + str(forest.power) + '"  fitness="' + str(forest.fitness) + '">\n'
            forests_xml += forest.store_xml()
            forests_xml += '</forest>\n'
        return forests_xml


class Experiment():
    def __init__(self, input_row, output_row, file_string):
        """getting initial data and making initial collection.
        """
        self._fullInput = input_row
        self._fullOutput = output_row
        self.count = 0
        self.fitness = 0
        self.outcast_address = file_string
        self.init_collection = ForestCollection(self._fullInput, self._fullOutput)
        self._xml_store = '<?xml version="1.1" encoding="UTF-8" ?>\n<experiment>\n'

    def start_experiment(self, stopping_criteria):
        """
        Just experiments. While stopping criteria is not actual executing experiment,
        storing results to xml spawning new generation (selecting, crossing, mutating) and so on.
        """
        experimental_collection = self.init_collection
        while not (stopping_criteria(self)):
            print 'generation = ', self.count
            print '|-act'
            experimental_collection.execute()

            self.fitness = experimental_collection.best_fitness
            self.count += 1
            self._xml_store += '<iteration best_fitness="' + str(self.fitness) + '" generation="' + str(
                self.count) + '">\n'
            self._xml_store += experimental_collection.store_xml()
            self._xml_store += '</iteration>\n'
            print '|-spawn'
            experimental_collection = ForestCollection(previous_generation=experimental_collection)
            print '|- mutate'
            experimental_collection.mutate()
        self._xml_store += '</experiment>'
        outc = open(self.outcast_address, 'w')
        outc.write(self._xml_store)
        outc.close()
