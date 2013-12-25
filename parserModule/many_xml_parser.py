__author__ = 'martolod'

import xml.etree.ElementTree as ElementTree

LIST_OF_ENTERS = ['inflow_noizd', 'outflow', 'trash']
inputs = ['2013_12_25-03_32_49_experiment' + str(i) + '.xml' for i in xrange(3)]

geners = 15
maximums = [[] for i in range(geners)]
averages = [[] for i in range(geners)]
trashinp = [[] for i in range(geners)]
median = [[] for i in range(geners)]
average = [[] for i in range(geners)]

for iter_input in inputs:
    tree = ElementTree.parse('../outflowData/' + iter_input)
    root = tree.getroot()
    i = 0
    for generation in root:
        localTrash = 0
        fitnesses = []
        localAvg = 0
        localMed = 0
        for forest in generation:
            fitnesses.append(float(forest.attrib['fitness']))
            for tree in forest:
                if tree.attrib['input'] == 'trash':
                    localTrash += 1
                if tree.attrib['input'] == 'inflow_noizd':
                    for node in tree:
                        if node.attrib['function'] == 'MedianFilter':
                            localMed += 1
                        elif node.attrib['function'] == 'MovingAverage':
                            localAvg += 1
        average[i].append(localAvg)
        median[i].append(localMed)
        trashinp[i].append(localTrash)
        maximums[i].append(max(fitnesses))
        averages[i].append(sum(fitnesses) / len(fitnesses))
        i += 1

outfile = open('result.csv', 'w')
outfile.writelines('max_max;min_max;avg_max;max_avg;min_avg;avg_avg;trashdata;MovingAverage;Median;' + '\n')
for i in range(geners):
    outline = str(max(maximums[i])) + ';' + str(min(maximums[i])) + ';' + str(
        sum(maximums[i]) / len(maximums[i])) + ';' + str(max(averages[i])) + ';' + str(min(averages[i])) + ';' + str(
        sum(averages[i]) / len(averages[i])) + ';' + str(sum(trashinp[i]) / len(trashinp[i])) + ';' + str(
        sum(average[i]) / len(average[i])) + ';' + str(sum(median[i]) / len(median[i])) + ';'
    outfile.writelines(outline + '\n')
outfile.close()